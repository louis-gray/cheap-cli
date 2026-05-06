# cheap-cli

Three CLI tools that delegate I/O-heavy, low-reasoning tasks to a cheap LLM (DeepSeek V4 Flash via OpenRouter, ~36x cheaper than Claude Opus on input). Designed to be called by Claude Code via Bash, but useful standalone.

## Why

Claude Code burns through usage limits on tasks that don't need its reasoning: reading dozens of files to answer one question, generating boilerplate, summarising long logs. These tools offload that work.

| Model | Input $/M | Output $/M |
|-|-|-|
| Claude Opus 4.7 | $5.00 | $25.00 |
| Claude Sonnet 4.6 | $3.00 | $15.00 |
| DeepSeek V4 Flash | $0.14 | $0.28 |

Caveat: Anthropic's prompt caching cuts effective Opus input to ~$1.49/M (74-94% cache hit rate typical), so the realised gap is closer to ~10x. Output is where the savings concentrate (90x cheaper). V4 Flash also has a 1M-token context, so even big repo sweeps fit.

## Install

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```sh
uv tool install --from git+https://github.com/grayscaled-dev/cheap-cli cheap-cli
```

Three executables land on `PATH`: `ask-cheap`, `write-cheap`, `summarize-cheap`.

### API key

Get a key from [openrouter.ai/settings/keys](https://openrouter.ai/settings/keys). Pick one of the setups below — the tools check env first, then the OS keystore.

#### macOS

Store in Keychain (recommended):

```sh
security add-generic-password -a "$USER" -s openrouter -U -w   # paste key at prompt
```

That's it. The tools fall back to Keychain automatically when `OPENROUTER_API_KEY` is unset.

For slightly faster invocation (avoids a subprocess per call), also export at shell start:

```fish
# fish
echo 'set -gx OPENROUTER_API_KEY (security find-generic-password -a $USER -s openrouter -w 2>/dev/null)' > ~/.config/fish/conf.d/openrouter.fish
```

```bash
# bash/zsh
echo 'export OPENROUTER_API_KEY=$(security find-generic-password -a "$USER" -s openrouter -w 2>/dev/null)' >> ~/.bashrc
```

#### Linux

Store in libsecret (gnome-keyring, KWallet, or any Secret Service provider). Install if needed:

```sh
sudo pacman -S libsecret           # Arch / CachyOS
sudo apt install libsecret-tools   # Debian / Ubuntu
sudo dnf install libsecret         # Fedora
```

Then store the key:

```sh
echo -n 'sk-or-v1-...' | secret-tool store --label='OpenRouter' service openrouter account "$USER"
```

The tools fall back to libsecret automatically. Headless servers without an unlocked keyring should use the env-var path instead:

```sh
# in ~/.bashrc or ~/.config/fish/conf.d/openrouter.fish
export OPENROUTER_API_KEY='sk-or-v1-...'
```

#### Windows

Set as a persistent user environment variable in PowerShell:

```powershell
[Environment]::SetEnvironmentVariable('OPENROUTER_API_KEY', 'sk-or-v1-...', 'User')
```

Restart your terminal to pick it up. For Credential Manager integration, set the env var in your PowerShell profile from the stored credential — the tools don't auto-fetch from Credential Manager since it has no uniform CLI like `security` or `secret-tool`.

### Override account/service

Both keystore lookups default to `account = $USER`, `service = openrouter`. Override per-call or globally:

```sh
export CHEAP_KEYCHAIN_ACCOUNT=alt-user
export CHEAP_KEYCHAIN_SERVICE=openrouter-work
```

## Usage

```fish
# Read files, answer a question
ask-cheap "where is auth handled?" src/**/*.py
ask-cheap "what changed in this diff?" - < /tmp/patch.diff

# Read a web URL — vendor docs, blog posts, RFCs, GitHub issues
ask-cheap "what's the rate limit on this API?" https://docs.example.com/limits
ask-cheap "summarise the design decisions" https://github.com/foo/bar/issues/123

# Generate boilerplate to stdout
write-cheap "pytest fixture for an authenticated FastAPI client"
write-cheap --lang fish "completion for foo --bar --baz" > completions/foo.fish

# Summarise a doc/log/url
summarize-cheap ci.log
go test -v ./... | summarize-cheap --bullets 5
summarize-cheap https://example.com/long-rfc.html --bullets 8
```

URL handling: HTTP(S) URLs are fetched directly. HTML is stripped to plain text via tag-removal — works well for static docs (most vendor sites, GitHub, Markdown-rendered pages). SPAs that render client-side return mostly nav cruft; use Claude's WebFetch for those.

## Configuration

| Var | Default | Purpose |
|-|-|-|
| `OPENROUTER_API_KEY` | *required* | OpenRouter auth |
| `CHEAP_MODEL` | `deepseek/deepseek-v4-flash` | Default model (any OpenRouter ID) |
| `CHEAP_REASONING` | unset | `low` / `medium` / `high` / `xhigh` |
| `CHEAP_LOG` | `~/.local/share/cheap-cli/usage.jsonl` | `off` to disable |
| `CHEAP_TIMEOUT` | `120` | Seconds |

Per-invocation: `--model`, `--reasoning`.

## Use with Claude Code

Append this to `~/.claude/CLAUDE.md`:

```
# Cheap-model delegation

Three CLI tools route to a cheap, large-context model (DeepSeek V4 Flash via
OpenRouter, ~36x cheaper than Opus on input list price, ~10x with caching).
**Default to delegation** for I/O-heavy, low-reasoning tasks. Skip only for
architecture, debugging, security-critical code, or anything where wrong > slow.

- ask-cheap "<question>" <files-or-urls>  reading >2 files / >500 lines, OR
                                          any web URL (vendor docs, blog
                                          posts, RFCs, GitHub issues). The
                                          tool fetches HTTP(S) URLs and
                                          strips HTML automatically.
- write-cheap "<description>"             boilerplate (tests, fixtures,
                                          fish/bash completions, repetitive
                                          configs, CRUD scaffolds). Also doc
                                          transcription when output will be
                                          >500 words AND source is structured
                                          (CHANGELOG entries, API refs,
                                          runbook updates). Not for nuanced
                                          prose, decision capture, or voice-
                                          sensitive notes (vault, daily
                                          notes, commit msgs).
- summarize-cheap <file|url|->            long logs, vendor docs, RFCs where
                                          only the gist matters

**Default delegation triggers — use cheap-cli unless the task needs reasoning:**
- Reading any URL for research, vendor docs, or API references → ask-cheap
- Looking up one fact across multiple files → ask-cheap
- Skimming a long log/output for the gist → summarize-cheap
- Generating any boilerplate >20 lines → write-cheap

Prefer Claude's WebFetch only for SPAs / dynamic pages where ask-cheap returns
mostly nav cruft. Pass paths and URLs, not contents — the tools fetch/read
themselves. If output looks wrong, fall back to doing the work yourself.
```

## Privacy & limits

- Anything you pass to these tools leaves your machine and goes to OpenRouter → DeepSeek. **Don't pass secrets, private keys, or NDA'd material.**
- Output occasionally has subtle errors. Treat it as a first draft, not a final answer.
- No retry beyond one backoff. Hard failures bubble up as exit codes 1/2/3.

## Usage log

Every successful call appends a JSON line to `~/.local/share/cheap-cli/usage.jsonl`:

```json
{"ts":"2026-05-03T14:21:09Z","tool":"ask-cheap","model":"deepseek/deepseek-v4-flash","prompt_tokens":12450,"completion_tokens":420,"cost_usd":0.001863,"args_hash":"a1b2c3"}
```

No prompt bodies or file contents are logged — metadata only.

## License

MIT.
