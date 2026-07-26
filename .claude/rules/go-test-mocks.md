---
paths:
  - "**/*_test.go"
---

# Go unit tests: mocks are generated, never hand-rolled

**Never hand-roll a test double for an interface.** No `stubFoo`, no
`fakeBar`, no `recordingBaz` struct written by hand to satisfy an interface a
test needs. Generate the mock with **[uber-go/mock](https://github.com/uber-go/mock)**
(`go.uber.org/mock`, the maintained fork of golang/mock) and use that.

Hand-rolled doubles drift from the interface, silently implement stale method
sets, and carry assertion logic that belongs in the test. A generated mock
tracks the interface by construction and fails loudly when it stops matching.

## How

Add the dependency and the generator:

```bash
go get go.uber.org/mock/gomock
go get -tool go.uber.org/mock/mockgen
```

Put a `//go:generate` directive next to the interface, so the mock is
regenerated from the source of truth rather than edited:

```go
//go:generate go tool mockgen -source=handler.go -destination=mocks_test.go -package=main
```

Then `go generate ./...`, and **commit the generated file** — CI does not run
`go generate`.

Write expectations on the mock instead of asserting on captured fields:

```go
ctrl := gomock.NewController(t)
relay := NewMockrelayer(ctrl)
relay.EXPECT().
    Relay(gomock.Any(), gomock.Any()).
    DoAndReturn(func(w http.ResponseWriter, _ *http.Request) error {
        w.WriteHeader(http.StatusOK)
        return nil
    })

downloads := NewMockdownloadRecorder(ctrl)
downloads.EXPECT().Record(gomock.Any(), metrics.Download{Repository: "demo/hello"})
```

`gomock.NewController(t)` registers its own cleanup, so unmet expectations fail
the test without an explicit `defer ctrl.Finish()`.

To assert something *never* happens, say so — it reads better than counting
calls on a hand-rolled spy:

```go
downloads.EXPECT().Record(gomock.Any(), gomock.Any()).Times(0)
```

## What this rule does not cover

- **Real servers and containers.** An `httptest.Server`, or a real dependency in
  a container, is not a mock — it is the real implementation under test
  conditions. Prefer it where a test can afford it, and keep using it.
- **Plain value fixtures.** A struct literal used as test data is not a double.
- **Interfaces you do not own.** Generate against the interface you depend on;
  do not hand-write a double because the interface lives in another module.

If a project's spec forbids code generation outright, that conflict is real —
raise it rather than silently hand-rolling a double.
