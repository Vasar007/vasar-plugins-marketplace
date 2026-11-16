// Replays the graders of one eval case on kept runs of `claude plugin eval`, by the rules of Claude Code 2.1.325.
// It replays regex graders on last_message, mock_calls, and trace, and tool_used graders. It skips the others.
// It prints one tab-separated line for each grader of each run. Exit code 1: a grader fails. 2: a wrong input.
import fs from 'node:fs';
import path from 'node:path';
import { parseArgs } from 'node:util';
import { fileURLToPath } from 'node:url';

const USAGE = 'Usage: node tests/evals/replay_graders.mjs --case <case folder> <run folder>...';
// The prefix of the output of a call that a mock stopped. The nonce of the run follows it.
const ABORT_PREFIX = 'eval aborted by mock';
// The value starts at a character that is not a space. So a long line of spaces does not cost square time.
const KEY_LINE = /^([A-Za-z_][\w-]*):(?:\s+(\S.*)?)?$/;
// The front matter rule of Claude Code 2.1.325. The closing --- can also be inside a line.
const FRONT_MATTER = /^---\s*\n([\s\S]*?)---\s*\n?/;
// The field that the body of a grader file fills when the front matter does not set it.
const BODY_FIELD = { llm: 'criteria', baseline: 'criteria', regex: 'pattern' };
// A plain value that YAML reads in another way: a comment, a mapping, or an indicator character.
const PLAIN_UNSAFE = /\s#|:(?:\s|$)|^[[\]{}#&*!|>%@`,]|^[-?](?:\s|$)/;

export class InputError extends Error {
  name = 'InputError';
}

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
  if (PLAIN_UNSAFE.test(text)) throw new InputError(`plain value that the replay cannot read: ${text}`);
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

function splitFrontMatter(text) {
  const clean = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
  const found = clean.match(FRONT_MATTER);
  if (found) return { front: found[1], body: clean.slice(found[0].length) };
  if (/^---\s*\n/.test(clean)) throw new InputError('the front matter has no closing --- line');
  return null;
}

// Read the YAML front matter of a grader file. It reads only the forms that the grader files use.
// Each line has one key. Its value is plain, single-quoted, double-quoted, or a one-line flow mapping.
// Returns null for a file without front matter. Claude Code skips such a grader file.
export function readFrontMatter(text) {
  const parts = splitFrontMatter(text);
  if (parts === null) return null;
  const fields = {};
  for (const line of parts.front.replace(/\r/g, '').split('\n')) {
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
    // Claude Code also gives an empty text for an input that JSON cannot write.
    return '';
  }
}

function serverName(name) {
  return name.replace(/[^a-zA-Z0-9_-]/g, '_');
}

function readTrace(tracePath) {
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
  return trace;
}

// Collect the tool calls of a trace with their results, and the text of the last assistant message.
function readCalls(trace) {
  const toolCalls = [];
  const byId = new Map();
  let lastMessage = '';
  for (const entry of trace) {
    const content = entry?.message?.content;
    if (!Array.isArray(content)) continue;
    if (entry.type === 'assistant') {
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
    } else if (entry.type === 'user') {
      for (const part of content) {
        const call = part?.type === 'tool_result' ? byId.get(part.tool_use_id) : undefined;
        if (call === undefined) continue;
        call.output = resultText(part.content);
        call.isError = part.is_error === true;
      }
    }
  }
  return { toolCalls, lastMessage };
}

// Read the mock specs of a kept run: the names of the mocked tools, and the nonce of the run.
function readMocks(mocksDir) {
  const mocked = new Set();
  let nonce = null;
  const specs = fs.existsSync(mocksDir) ? fs.readdirSync(mocksDir).filter((name) => name.endsWith('.json')) : [];
  for (const name of specs.sort()) {
    const file = path.join(mocksDir, name);
    try {
      const spec = JSON.parse(fs.readFileSync(file, 'utf8'));
      if (typeof spec?.registeredName !== 'string') throw new InputError('the mock spec has no registeredName text');
      nonce = spec.nonce ?? nonce;
      const server = serverName(spec.registeredName);
      for (const tool of spec.tools ?? []) mocked.add(`mcp__${server}__${serverName(tool.name)}`);
    } catch (error) {
      throw new InputError(`${file}: ${error.message}`, { cause: error });
    }
  }
  return { mocked, nonce };
}

// Read the trace and the mock specs of a kept run folder.
export function readRun(runDir) {
  const trace = readTrace(path.join(runDir, 'out', 'trace.jsonl'));
  return { trace, ...readCalls(trace), ...readMocks(path.join(runDir, 'out', 'mocks')) };
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
    if (run.mocked.size === 0) {
      return { unavailable: 'no mock stand-ins were active in this run (--mocks off, or no mocks/ directory '
        + 'applies to this case) \u2014 a mock_calls grader has nothing to check' };
    }
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
  const caseYaml = path.join(caseDir, 'case.yaml');
  if (fs.existsSync(caseYaml) && /^graders\s*:/m.test(fs.readFileSync(caseYaml, 'utf8'))) {
    throw new InputError(`${caseYaml} lists graders, and the replay reads only graders/*.md`);
  }
  const dir = path.join(caseDir, 'graders');
  if (!fs.existsSync(dir)) throw new InputError(`no graders folder: ${dir}`);
  const graders = [];
  for (const name of fs.readdirSync(dir).filter((file) => file.endsWith('.md')).sort()) {
    const file = path.join(dir, name);
    try {
      const text = fs.readFileSync(file, 'utf8');
      const fields = readFrontMatter(text);
      if (fields === null) continue;
      const grader = { name: path.basename(name, '.md'), ...fields };
      if (typeof grader.type !== 'string') throw new InputError('the front matter has no type key');
      const field = BODY_FIELD[grader.type];
      const body = splitFrontMatter(text).body.trim();
      if (field && grader[field] === undefined && body.length > 0) grader[field] = body;
      graders.push(grader);
    } catch (error) {
      throw new InputError(`${file}: ${error.message}`, { cause: error });
    }
  }
  if (graders.length === 0) throw new InputError(`no grader file with front matter in ${dir}`);
  return graders;
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

// Node.js loads a script by its real path. So the real paths tell if this file is the script, also through a symlink.
function isScript() {
  const script = process.argv[1];
  if (!script || !fs.existsSync(script)) return false;
  return fs.realpathSync(script) === fs.realpathSync(fileURLToPath(import.meta.url));
}

if (isScript()) {
  // A reader that closes the pipe early, for example `head`, is not an error of the replay.
  process.stdout.on('error', (error) => {
    if (error.code !== 'EPIPE') throw error;
  });
  process.exitCode = main(process.argv.slice(2));
}
