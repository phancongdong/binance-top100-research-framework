# Original source for recruiter review

[auto_trade_smc_mtf.py](auto_trade_smc_mtf.py) is a selectively redacted original
source file, not the newly written offline demo. It retains 124 top-level
functions/classes across 4,798 lines; 113 definitions preserve their original
Python syntax trees. State persistence/recovery, data-provider handling, retries,
the main loop and order-management code remain available for inspection.

Private Fibonacci parameter/route tables, selection files/hashes, strategy
construction and dependent frozen assertions were removed or replaced by empty
interfaces. Identifying order-prefix and activation settings were redacted.
Non-Fibonacci strategy code and configuration remain by the owner's request.
Some removed interfaces keep their original names; those names contain no
removed parameter data. No private runtime dataset or account records accompany
this source.

An explicit guard stops execution before imports or initialization. The original
private dependencies are not distributed, and this file is not a runnable or
deployable release. No exchange call or deployment was used to verify it.
Verification covers syntax, retained structure, removed literals and the guard;
passing demo tests is not validation of this runner's trading behavior.

For runnable examples, return to the root README and use `research_framework`
or `operations_demo`. AI-assisted development and human-directed publication
are disclosed; no investment-performance or independent-programming claim is
established by this artifact.
