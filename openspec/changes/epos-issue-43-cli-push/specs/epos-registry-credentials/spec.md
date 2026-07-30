## ADDED Requirements

### Requirement: The CLI can obtain registry credentials by itself

`epos` SHALL provide `registry login` and `registry logout` subcommands, so that
publishing to an authenticated registry requires no other OCI client to be
installed.

#### Scenario: A fresh machine can publish
- **WHEN** a user with neither `docker` nor `oras` installed logs in to a
  registry with `epos` and pushes a skill
- **THEN** both succeed

#### Scenario: Logging out removes the credential
- **WHEN** a user logs out of a registry and pushes to it again
- **THEN** the push is unauthenticated, and a registry requiring authentication
  refuses it

#### Scenario: The command names what is being logged in to
- **WHEN** the command tree is inspected
- **THEN** the subcommands are under `registry`, because epos issues no
  credentials of its own and there is nothing to log in to called "epos"

### Requirement: Credentials are shared with the existing OCI ecosystem

Credentials SHALL be read from and written to the Docker configuration and the
platform's native credential helpers, so that a login performed by any of
`epos`, `docker`, `oras` or `helm` is usable by `epos`.

#### Scenario: An existing docker login is honoured
- **WHEN** a user has already authenticated to a registry with another OCI client
  and pushes with `epos`
- **THEN** the push authenticates, with no epos-specific login step

#### Scenario: An epos login is usable by other clients
- **WHEN** a user logs in with `epos registry login` and then uses another OCI
  client against the same registry
- **THEN** that client finds the credential

#### Scenario: A native credential helper is used where one is configured
- **WHEN** the platform has a credential helper configured
- **THEN** the credential is read through the helper rather than from the
  configuration file

### Requirement: Credential sources resolve in a stated order

Credential resolution SHALL take the first match from: an explicitly configured
registry-configuration path; the path named by the Docker configuration
environment variable; the default Docker configuration together with the native
helpers; and otherwise no credential at all.

#### Scenario: An explicit path wins
- **WHEN** a registry-configuration path is given on the command line and a
  default configuration also holds a credential for that registry
- **THEN** the credential from the given path is used

#### Scenario: The environment overrides the default location
- **WHEN** no path is given on the command line and the Docker configuration
  environment variable names a directory
- **THEN** the configuration in that directory is used

#### Scenario: Anonymous is a valid outcome
- **WHEN** no credential is found for the target registry
- **THEN** the request is made anonymously, and a registry that permits anonymous
  access succeeds

#### Scenario: A rejected anonymous push says what to do
- **WHEN** a registry refuses an unauthenticated push
- **THEN** the error names the registry and the command that would log in to it

### Requirement: No secret is ever passed in a command-line argument

The login command SHALL accept a password or token only on standard input or
through an echo-suppressed prompt, and SHALL NOT provide a flag that takes a
password or token as its value.

#### Scenario: There is no password flag
- **WHEN** the login command's flags are inspected
- **THEN** none of them takes a password or token value, deliberately unlike the
  equivalent flag on other clients

#### Scenario: A piped secret is accepted
- **WHEN** a token is piped to the login command with the standard-input option
- **THEN** the login succeeds and the token appears in no argument list

#### Scenario: An interactive login does not echo
- **WHEN** standard input is a terminal and no secret was piped
- **THEN** the user is prompted and the typed characters are not echoed

#### Scenario: A non-interactive login with no secret fails clearly
- **WHEN** standard input is not a terminal and no secret was supplied on it
- **THEN** the command fails saying how to supply one, rather than hanging on a
  prompt nobody can answer or logging in with an empty secret

#### Scenario: A login states whose credential it is
- **WHEN** a login is attempted with no user identified
- **THEN** the command fails asking for one, because a stored credential that
  names no user cannot be matched to a registry account

### Requirement: A stored credential is not readable by other users

A credential written by `epos` SHALL be stored so that only its owner can read
it, and SHALL be written without leaving a partially written file behind.

#### Scenario: The credential file is owner-only
- **WHEN** a login writes a credential to a configuration file on a system with
  file permissions
- **THEN** the file is readable and writable only by its owner, and its
  containing directory is accessible only to its owner

#### Scenario: An interrupted write leaves the previous credential intact
- **WHEN** a login is interrupted partway through writing the configuration
- **THEN** the previous configuration is still readable and is not truncated

#### Scenario: Storing without a helper is not presented as encryption
- **WHEN** no native credential helper is available and the credential is stored
  in the configuration file
- **THEN** the command's own help says plainly that the credential is stored in a
  file rather than encrypted

### Requirement: No credential appears in output

No command SHALL write a password, token or authorization header to its output,
its error messages or its logs.

#### Scenario: An authentication failure reveals nothing
- **WHEN** a registry rejects a credential
- **THEN** the error names the registry and the failure, and contains neither the
  credential nor the header it was sent in

### Requirement: Every command that talks to a registry uses the same credentials

The credential-bearing client SHALL be built in one place and used by every
command that contacts a registry, including the commands that write signatures
and attestations.

#### Scenario: Signing an artifact in an authenticated registry works
- **WHEN** a skill in a registry requiring authentication is signed
- **THEN** the signature is written to the registry, which it cannot be while the
  signing path is unauthenticated

#### Scenario: Reading commands authenticate too
- **WHEN** a private registry is pulled from, verified against, listed or
  searched by a logged-in user
- **THEN** each of those commands authenticates with the same credential

#### Scenario: A public registry still works for a user with no credential for it
- **WHEN** a user with credentials stored for one registry reads from a
  different, public registry
- **THEN** the read succeeds anonymously, because credential resolution is per
  registry and finding none is not an error

#### Scenario: A stale credential fails visibly rather than silently
- **WHEN** a stored credential for a registry is no longer valid and a command
  that previously succeeded anonymously now sends it
- **THEN** the command fails with a message naming the registry and saying the
  stored credential was rejected, so the cause is the credential rather than an
  unexplained regression

#### Scenario: Pulls stay counted while authenticated
- **WHEN** an authenticated pull is made through a registry that counts verified
  downloads
- **THEN** the download is still recorded as verified, so authentication has not
  displaced the download-reporting header
