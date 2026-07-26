---
paths:
  - "**/*_test.go"
---

# Go unit tests: assert with a library, not hand-rolled comparisons

**Use [testify](https://github.com/stretchr/testify)** (`github.com/stretchr/testify`)
rather than hand-written `if got != want { t.Errorf(...) }` blocks.

Hand-rolled comparisons are where test code rots: each one re-invents its own
message format, most print the values in a different order from every other,
deep comparisons get written as `reflect.DeepEqual` with a message that does
not say what differed, and a `t.Errorf` that should have been `t.Fatalf` leaves
the test running on state it already knows is wrong.

## How

```go
import (
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
)

func TestThing(t *testing.T) {
    cfg, err := ParseFrontmatter(src)
    require.NoError(t, err)              // stop here — nothing below is meaningful
    require.NotNil(t, cfg)

    assert.Equal(t, "reviewer", cfg.Name())          // want, got — in that order
    assert.Contains(t, cfg, "custom-field")
    assert.Len(t, entries, 3)
    assert.ElementsMatch(t, []string{"a", "b"}, got) // order-independent
}
```

**`require` stops the test, `assert` keeps going.** Reach for `require` when
everything after it depends on the check — an error, a nil pointer, a length
you are about to index into. Use `assert` when independent facts are being
checked and you would rather see all the failures at once than fix them one run
at a time.

Testify's argument order is `(t, expected, actual)`. Getting it backwards
produces a message that blames the wrong side, so read it twice.

## Prefer the specific assertion

`assert.Equal` works for everything, which is exactly why it is worth avoiding
when something narrower exists — the narrower one produces a better failure
message:

| Instead of | Use |
| --- | --- |
| `assert.Equal(t, true, ok)` | `assert.True(t, ok)` |
| `assert.Equal(t, nil, err)` | `assert.NoError(t, err)` — or `require.NoError` |
| `assert.Equal(t, 3, len(xs))` | `assert.Len(t, xs, 3)` |
| `assert.True(t, strings.Contains(s, x))` | `assert.Contains(t, s, x)` |
| `assert.True(t, errors.Is(err, ErrX))` | `assert.ErrorIs(t, err, ErrX)` |
| sorting both sides before comparing | `assert.ElementsMatch` |

Add a message when the assertion alone will not tell a reader *why* it matters:

```go
assert.Equal(t, first, second,
    "identical inputs must produce identical layers; SPEC 2.4 requires it")
```

## What this rule does not cover

- **Table-driven tests stay table-driven.** This is about how a case asserts,
  not about how cases are organised.
- **Benchmarks and fuzz targets** have no assertions to speak of; leave them.
- **Golden-file comparisons** may legitimately diff whole files with a
  purpose-built helper rather than `assert.Equal` on a huge string.

Mocks are covered separately by [go-test-mocks](go-test-mocks.md): generated
with uber-go/mock, never hand-rolled.
