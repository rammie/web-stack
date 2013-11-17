#! /usr/bin/env python
# encoding: utf-8
import os
import platform
import sys


def options(ctx):
    toolsdir = os.path.join(ctx.path.abspath(), "waftools")
    ctx.load("venv", tooldir=toolsdir)
    ctx.load("modules", tooldir=toolsdir)


def configure(ctx):
    print("→ configuring the project in " + ctx.path.abspath())
    toolsdir = os.path.join(ctx.path.abspath(), "waftools")
    ctx.load("venv", tooldir=toolsdir)
    ctx.load("modules", tooldir=toolsdir)
    ctx.env.SRCPATH = ctx.path.abspath()


def build(ctx):
    ctx.module(
        "pkg-config-0.27.1", "--disable-debug --with-internal-glib",
        source="../bin/activate", target="../bin/pkg-config")
    ctx.module("libpng-1.5.13", source="../bin/pkg-config", target="../bin/libpng-config")
    ctx.module("libevent-2.0.21-stable", source="../bin/pkg-config", target="../lib/libevent.a")
    ctx.module("zeromq-3.2.2", source="../bin/pkg-config", target="../lib/libzmq.a")

    ctx(rule=ctx.build_postgresql, source="../bin/pkg-config", target="../bin/postmaster")
    ctx(rule=ctx.build_redis, source="../bin/pkg-config", target="../bin/redis-server")

    pkg = os.path.join(ctx.path.abspath(), "3rdparty", "site-packages")
    if sys.platform == "darwin":
        ctx(rule=ctx.build_gfortran, source="../bin/pkg-config", target="../bin/gfortran")
        platform_deps = ["../bin/gfortran"]

        # Readline does not build on Mavericks and is no longer needed.
        if (platform.mac_ver()[0] < "10.9"):
            readlinetar = "%s/readline-6.2.4.1.tar.gz" % pkg
            readlinecmd = ctx.venv("easy_install --no-find-links %s && touch ${TGT}" % readlinetar)
            ctx(rule=readlinecmd, source="../bin/pkg-config", target="../.readline-done")
            platform_deps = ["../.readline-done"]

    else:
        # We assume that a fortran compiler with lapack is installed.
        # It may be installed using:
        # sudo apt-get install liblapack-dev gfortran
        ctx(rule=ctx.build_blas, source="../bin/pkg-config", target="../lib/libblas.a")
        platform_deps = ["../lib/libblas.a"]

    # Install numpy separately due to bug in scipy install script.
    site_packages = os.path.join("..", "lib", "python2.7", "site-packages")
    numpy = os.path.join(site_packages, "numpy", "__init__.py")
    ctx(rule=ctx.venv("pip install numpy==1.6.2 --no-index -f file://%s" % pkg),
        source=platform_deps, target=numpy)

    # Install gevent separately due to include path issues.
    gevent = os.path.join(site_packages, "gevent", ".done")
    ctx(rule=ctx.build_gevent, source="../lib/libevent.a", target=gevent)

    # Install cvxopt separately due to misplaced setup.py file.
    cvxopt = os.path.join(site_packages, "cvxopt", "__init__.py")
    ctx(rule=ctx.build_cvxopt, source=numpy, target=cvxopt)

    # Install iPython separately from requirements in order to build mathjax.
    reqs_ipython = "%s/requirements-ipython.txt" % ctx.path.abspath()
    ctx(
        rule=ctx.venv("pip install --no-index -f file://%s -r %s" % (pkg, reqs_ipython)),
        source=platform_deps + [numpy],
        target="../bin/ipython")
    ctx.add_manual_dependency("../bin/ipython", ctx.path.find_node("requirements-ipython.txt"))
    ctx(rule=ctx.build_mathjax, source="../bin/ipython", target="../.mathjax-done")

    reqs = "%s/requirements.txt" % ctx.path.abspath()
    ctx(
        rule=ctx.venv("pip install --no-index -f file://%s -r %s && touch ${TGT}" % (pkg, reqs)),
        source=platform_deps + [
            gevent,
            numpy,
            "../.mathjax-done",
            "../bin/ipython",
            "../lib/libevent.a",
            "../bin/libpng-config",
            "../lib/libzmq.a",
            "../bin/postmaster",
            "../bin/redis-server"
        ],
        target="../.requirements-done")
    ctx.add_manual_dependency("../.requirements-done", ctx.path.find_node("requirements.txt"))
    ctx(rule="touch ${TGT}", source="../.requirements-done", target="../../.build-done")
