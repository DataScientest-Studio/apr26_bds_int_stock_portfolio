# Convenience shim — the operator surface lives in Project/Structure/Makefile.
# Lets `make app`, `make on`, `make dashboard`, ... work from the repo root too.
help:
	@$(MAKE) --no-print-directory -C Project/Structure help
%:
	@$(MAKE) --no-print-directory -C Project/Structure $@
