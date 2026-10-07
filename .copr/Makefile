# COPR "make srpm" recipe: packs this checkout as the release tarball the spec
# expects, then builds the source RPM. COPR runs
#   make -f .copr/Makefile srpm outdir=<dir> spec=<path to spec>

spec ?= packaging/plasma-light-and-presence.spec
outdir ?= $(CURDIR)/srpm
top := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
version = $(shell rpmspec -q --srpm --qf '%{version}' $(spec))

srpm:
	command -v rpmbuild >/dev/null || dnf -y install rpm-build
	command -v git >/dev/null || dnf -y install git
	mkdir -p $(outdir)
	git -c safe.directory=$(top) -C $(top) archive --prefix=plasma-light-and-presence-$(version)/ \
	  -o $(outdir)/plasma-light-and-presence-$(version).tar.gz HEAD
	rpmbuild -bs \
	  --define "_sourcedir $(outdir)" \
	  --define "_srcrpmdir $(outdir)" \
	  --define "dist %{nil}" \
	  $(spec)

.PHONY: srpm
