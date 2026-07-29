---
paths:
  - "**/*.go"
  - "**/go.mod"
---

# Go CLIs: Cobra yes, Viper no — configuration is koanf

The [`cobra-viper`](../skills/cobra-viper/SKILL.md) skill is spf13's own, and its
**Cobra** half is the house standard: command-first architecture, a constructor
per command, no package-level state, `RunE` over `Run`, context-aware commands,
`cmd/` decoupled from the engine, in-memory CLI testing. Follow it.

**Do not use Viper.** Configuration is [koanf](https://github.com/knadh/koanf)
(`github.com/knadh/koanf/v2`). This is a standing preference, not a per-project
call, so the skill is left exactly as upstream wrote it and the exception lives
here instead — editing a vendored skill would lose the edit the next time it is
reinstalled.

## Translating the skill

Every Viper instance in the skill becomes a koanf instance; nothing else about
the structure changes. Where the skill says:

```go
func NewRootCmd() *cobra.Command {
    v := viper.New()
    // …
    rootCmd.AddCommand(NewServeCmd(v))
}
```

write:

```go
func NewRootCmd() *cobra.Command {
    k := koanf.New(".")
    // …
    rootCmd.AddCommand(NewServeCmd(k))
}
```

The pieces that replace what Viper did implicitly:

| Viper | koanf |
|---|---|
| `viper.BindPFlags(cmd.Flags())` | `k.Load(posflag.Provider(cmd.Flags(), ".", k), nil)` |
| `viper.SetConfigFile` / `ReadInConfig` | `k.Load(file.Provider(path), yaml.Parser())` |
| `viper.SetEnvPrefix` + `AutomaticEnv` | `k.Load(env.Provider("MYCLI_", ".", transform), nil)` |
| `viper.Unmarshal(&cfg)` | `k.Unmarshal("", &cfg)` |

Load in precedence order — defaults, then file, then environment, then flags —
because koanf merges in call order and has no equivalent of Viper's implicit
precedence table. That explicitness is the reason for the preference: with
koanf, which source won is the order you can read in the function.

Keep the skill's rule that the engine package imports neither the CLI nor the
configuration library. `cmd/` unmarshals into a plain config struct and passes
that in; nothing downstream knows koanf exists, which is what makes the choice
cheap to revisit.

## Also from spf13

- [`go`](../skills/go/SKILL.md) — idiomatic Go: package design, errors,
  interfaces, concurrency, testing. Applies to any Go work here.
- [`go-spec-reviewer`](../skills/go-spec-reviewer/SKILL.md) — review a design
  doc or spec for a Go program *before* implementing it. See `AGENTS.md`.
