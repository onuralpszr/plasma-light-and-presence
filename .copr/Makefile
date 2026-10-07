# COPR "make srpm" recipe: packs this checkout as the release tarball the spec
# expects, then builds the source RPM. COPR runs
#   make -f .copr/Makefile srpm outdir=<dir> spec=<path to spec>

spec ?= packaging/plasma-sensord.spec
outdir ?= $(CURDIR)/srpm
top := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
version = $(shell rpmspec -q --srpm --qf '%{version}' $(spec))

srpm:
	command -v rpmbuild >/dev/null || dnf -y install rpm-build git
	mkdir -p $(outdir)
	git -c safe.directory=$(top) -C $(top) archive --prefix=plasma-sensord-$(version)/ \
	  -o $(outdir)/plasma-sensord-$(version).tar.gz HEAD
	rpmbuild -bs \
	  --define "_sourcedir $(outdir)" \
	  --define "_srcrpmdir $(outdir)" \
	  --define "dist %{nil}" \
	  $(spec)

.PHONY: srpm
