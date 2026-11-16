// Replays the graders of one eval case on kept runs of `claude plugin eval`, by the rules of Claude Code 2.1.325.
// It replays regex graders on last_message, mock_calls, and trace, and tool_used graders. It skips the others.
// It prints one tab-separated line for each grader of each run. Exit code 1: a grader fails. 2: a wrong input.
import fs from 'node:fs';
import path from 'node:path';
import { parseArgs } from 'node:util';
import { pathToFileURL } from 'node:url';

const USAGE = 'Usage: node tests/evals/replay_graders.mjs --case <case folder> <run folder>...';
// The prefix of the output of a call that a mock stopped. The nonce of the run follows it.
const ABORT_PREFIX = 'eval aborted by mock';
const KEY_LINE = /^([A-Za-z_][\w-]*):(?:\s+(.*))?$/;

export class InputError extends Error {}

function scalar(text) {
  if (text.startsWith("'")) {
    if (!text.endsWith("'") || text.length < 2) throw new InputError(`unclosed quote: ${text}`);
    return text.slice(1, -1).replace(/''/g, "'");
  }
  if (text.startsWith('"')) {
    try {
      return JSON.parse(text);
    } catch {
      throw new InputError(`double-quoted value that JSON cannot read: ${text}`);
    }
  }
  if (text === 'true' || text === 'false') return text === 'true';
  if (/^-?\d+$/.test(text)) return Number(text);
  return text;
}

function flowMapping(text) {
  const fields = {};
  for (const pair of text.slice(1, -1).split(',')) {
    const [key, ...rest] = pair.split(':');
    if (rest.length === 0) throw new InputError(`flow mapping entry without a colon: ${text}`);
    fields[key.trim()] = scalar(rest.join(':').trim());
  }
  return fields;
}

// Read the YAML front matter of a grader file. It reads only the forms that the grader files use:
// one key on each line, with a plain, single-quoted, or double-quoted value, or a one-line flow mapping.
export function readFrontMatter(text) {
  const lines = text.replace(/\r/g, '').split('\n');
  if (lines[0] !== '---') throw new InputError('the file does not start with a --- line');
  const end = lines.indexOf('---', 1);
  if (end === -1) throw new InputError('the front matter has no closing --- line');
  const fields = {};
  for (const line of lines.slice(1, end)) {
    if (line.trim() === '' || line.startsWith('#')) continue;
    const pair = KEY_LINE.exec(line);
    if (!pair) throw new InputError(`front matter line that the replay cannot read: ${line}`);
    const value = (pair[2] ?? '').trim();
    fields[pair[1]] = value.startsWith('{') && value.endsWith('}') ? flowMapping(value) : scalar(value);
  }
  return fields;
}

function resultText(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    const texts = content.map((part) => (part && typeof part === 'object' && 'text' in part ? String(part.text) : ''));
    return texts.join('');
  }
  return '';
}

function inputText(input) {
  try {
    return JSON.stringify(input) ?? '';
  } catch {
    return '';
  }
}

function serverName(name) {
  return name.replace(/[^a-zA-Z0-9_-]/g, '_');
}

// Read the trace and the mock specs of a kept run folder.
export function readRun(runDir) {
  const tracePath = path.join(runDir, 'out', 'trace.jsonl');
  if (!fs.existsSync(tracePath)) throw new InputError(`no trace: ${tracePath}`);
  const trace = [];
  for (const line of fs.readFileSync(tracePath, 'utf8').split('\n')) {
    const text = line.trim();
    if (!text) continue;
    try {
      trace.push(JSON.parse(text));
    } catch {
      // Claude Code also skips a line that is not JSON.
    }
  }
  const toolCalls = [];
  const byId = new Map();
  let lastMessage = '';
  for (const entry of trace) {
    const content = entry?.message?.content;
    if (entry?.type === 'assistant' && Array.isArray(content)) {
      const texts = [];
      for (const part of content) {
        if (part?.type === 'tool_use') {
          const call = { name: String(part.name ?? ''), input: part.input, inputText: inputText(part.input) };
          toolCalls.push(call);
          if (typeof part.id === 'string') byId.set(part.id, call);
        } else if (part?.type === 'text') {
          texts.push(String(part.text ?? ''));
        }
      }
      if (texts.length > 0) lastMessage = texts.join('\n');
    } else if (entry?.type === 'user' && Array.isArray(content)) {
      for (const part of content) {
        const call = part?.type === 'tool_result' ? byId.get(part.tool_use_id) : undefined;
        if (call === undefined) continue;
        call.output = resultText(part.content);
        call.isError = part.is_error === true;
      }
    }
  }
  const mocked = new Set();
  let nonce = null;
  const mocksDir = path.join(runDir, 'out', 'mocks');
  const specs = fs.existsSync(mocksDir) ? fs.readdirSync(mocksDir).filter((name) => name.endsWith('.json')) : [];
  for (const name of specs.sort()) {
    const spec = JSON.parse(fs.readFileSync(path.join(mocksDir, name), 'utf8'));
    nonce = spec.nonce ?? nonce;
    const server = serverName(spec.registeredName);
    for (const tool of spec.tools ?? []) mocked.add(`mcp__${server}__${serverName(tool.name)}`);
  }
  return { trace, toolCalls, lastMessage, mocked, nonce };
}

function verdictOf(call, nonce) {
  if (call.isError === undefined) return 'no_result';
  if (!call.isError) return 'ok';
  return (call.output ?? '').startsWith(`${ABORT_PREFIX} ${nonce}:`) ? 'abort' : 'tool_error';
}

// The mock_calls text: one JSON line for each call to a mocked tool, in the order of the trace.
export function mockCallsText(run) {
  return run.toolCalls
    .filter((call) => run.mocked.has(call.name))
    .map((call) => JSON.stringify({
      tool: call.name,
      input: call.input,
      ...(call.output !== undefined && { output: call.output }),
      ...(call.isError && { isError: true }),
      verdict: verdictOf(call, run.nonce),
    }))
    .join('\n');
}

function targetText(target, run) {
  if (target === 'last_message') return run.lastMessage;
  if (target === 'trace') return run.trace.map((entry) => JSON.stringify(entry)).join('\n');
  if (target === 'mock_calls') {
    if (run.mocked.size === 0) return { unavailable: 'no mock stand-ins were active in this run' };
    return mockCallsText(run);
  }
  return null;
}

function gradeRegex(grader, text) {
  const flags = grader.flags ?? '';
  const match = grader.match ?? 'contains';
  const once = new RegExp(grader.pattern, flags);
  if (match === 'contains') {
    return once.test(text) ? ['pass', `matched ${grader.pattern}`] : ['fail', `pattern not found in ${grader.target}`];
  }
  if (match === 'not_contains') {
    return once.test(text) ? ['fail', 'pattern found (expected absent)'] : ['pass', 'pattern absent as expected'];
  }
  if (match.startsWith('count:')) {
    const expected = parseInt(match.slice(6), 10);
    const found = (text.match(new RegExp(grader.pattern, flags.includes('g') ? flags : `${flags}g`)) ?? []).length;
    return [found === expected ? 'pass' : 'fail', `found ${found} matches (expected ${expected})`];
  }
  return ['fail', `unknown match mode "${match}" (use contains | not_contains | count:N)`];
}

function gradeToolUsed(grader, run) {
  const pattern = grader.input_match === undefined ? null : new RegExp(grader.input_match);
  const calls = run.toolCalls.filter((call) => call.name === grader.tool && (!pattern || pattern.test(call.inputText)));
  const count = calls.length;
  const min = grader.min ?? 1;
  const max = grader.max ?? Number.POSITIVE_INFINITY;
  const shown = max === Number.POSITIVE_INFINITY ? '∞' : max;
  const verdict = count >= min && count <= max ? 'pass' : 'fail';
  return [verdict, `${grader.tool} called ${count}x (expected ${min}..${shown})`];
}

// Grade one grader on one run. Returns [verdict, reason], and the verdict is pass, fail, or skip.
export function grade(grader, run) {
  try {
    if (grader.type === 'tool_used') return gradeToolUsed(grader, run);
    if (grader.type !== 'regex') return ['skip', `the replay does not run ${grader.type} graders`];
    const target = grader.target ?? 'last_message';
    const text = targetText(target, run);
    if (text === null) return ['skip', `the kept run does not hold the target ${JSON.stringify(target)}`];
    if (typeof text === 'object') return ['fail', text.unavailable];
    return gradeRegex({ ...grader, target }, text);
  } catch (error) {
    return ['fail', `grader threw: ${error.message}`];
  }
}

export function readGraders(caseDir) {
  const dir = path.join(caseDir, 'graders');
  if (!fs.existsSync(dir)) throw new InputError(`no graders folder: ${dir}`);
  return fs.readdirSync(dir).filter((name) => name.endsWith('.md')).sort().map((name) => {
    try {
      return { name: name.slice(0, -3), ...readFrontMatter(fs.readFileSync(path.join(dir, name), 'utf8')) };
    } catch (error) {
      throw new InputError(`${path.join(dir, name)}: ${error.message}`);
    }
  });
}

function oneLine(text) {
  return String(text).replace(/[\t\r\n]+/g, ' ');
}

export function main(argv, write = (line) => process.stdout.write(`${line}\n`)) {
  let graders;
  let runs;
  try {
    const { values, positionals } = parseArgs({
      args: argv, options: { case: { type: 'string' } }, allowPositionals: true,
    });
    if (!values.case || positionals.length === 0) throw new InputError('give --case and at least one run folder');
    graders = readGraders(values.case);
    runs = positionals.map((dir) => ({ dir, run: readRun(dir) }));
  } catch (error) {
    process.stderr.write(`error: ${error.message}\n${USAGE}\n`);
    return 2;
  }
  let failed = false;
  for (const { dir, run } of runs) {
    for (const grader of graders) {
      const [verdict, reason] = grade(grader, run);
      failed ||= verdict === 'fail';
      write([path.basename(path.resolve(dir)), grader.name, verdict, oneLine(reason)].join('\t'));
    }
  }
  return failed ? 1 : 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = main(process.argv.slice(2));
}
