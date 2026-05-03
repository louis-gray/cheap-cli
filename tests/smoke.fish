#!/usr/bin/env fish
# End-to-end smoke test. Requires OPENROUTER_API_KEY in env.

if test -z "$OPENROUTER_API_KEY"
    echo "smoke: OPENROUTER_API_KEY not set" >&2
    exit 1
end

cd (dirname (status --current-filename))/..

ask-cheap "what language is this written in?" cheap_cli/ask.py | grep -qi python
or begin; echo "smoke: ask-cheap failed" >&2; exit 1; end

echo "hello world" | summarize-cheap | string length -q
or begin; echo "smoke: summarize-cheap failed" >&2; exit 1; end

write-cheap --lang python "print hello world" | grep -q "print"
or begin; echo "smoke: write-cheap failed" >&2; exit 1; end

echo "smoke OK"
