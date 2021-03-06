""" Simple RPM package class. """

import fnmatch

from rpmvercmp import rpmvercmp

class Pkg(object):
    """ Simple "package", compatible with rpm. """

    def __init__(self, name, version, release=None, arch=None, epoch=None):
        self.name = str(name)
        self.version = str(version)
        if release is None:
            release = '1'
        self.release = str(release)
        if arch is None:
            arch = 'src'
        self.arch = str(arch)

        # Magic property, see below
        self.epoch = epoch

    def __str__(self):
        return self.ui_nevra

    def __eq__(self, o):
        if self.name != o.name:
            return False
        if self.verCMP(o) != 0:
            return False
        return self.arch == o.arch

    def __gt__(self, o):
        if self.name > o.name:
            return True
        if self.name != o.name:
            return False

        val = self.verCMP(o)
        if val > 0:
            return True
        if val != 0:
            return False

        if self.arch > o.arch:
            return True

        return False

    def __lt__(self, o):
        if self.name < o.name:
            return True
        if self.name != o.name:
            return False

        val = self.verCMP(o)
        if val < 0:
            return True
        if val != 0:
            return False

        if self.arch < o.arch:
            return True

        return False

    def __ge__(self, o):
        return not self.__lt__(o)
    def __le__(self, o):
        return not self.__gt__(o)

    # This is slightly different to rpm and/or koji.
    #  In rpm epoch=None is the same as epoch='0' for testing, but in theory
    # you can see the difference.
    #  In koji roughly follows rpm (not sure if it converts epoch='0' or
    # just treats them the same internally, as rpm does).
    #  For spkg.Pkg() epoch=None means don't compare epochs ... this is because
    # we have situtations where we don't get epochs
    @property
    def epoch(self):
        if self.__epoch is None:
            return '0'
        return self.__epoch

    @epoch.setter
    def epoch(self, epoch):
        if epoch is not None:
            epoch = str(epoch)
        self.__epoch = epoch

    def verCMP(self, o): # Old yum API name, eh.
        val = 0
        if self.__epoch is not None and o.__epoch is not None:
            val = rpmvercmp(self.epoch, o.epoch) # Should just be ints, but eh
        if val != 0:
            return val
        val = rpmvercmp(self.version, o.version)
        if val != 0:
            return val
        val = rpmvercmp(self.release, o.release)
        return val

    def verEQ(self, other):
        """ Compare package to another one, only rpm-version equality. """
        return self.verCMP(other) == 0
    def verNE(self, other):
        """ Compare package to another one, only rpm-version inequality. """
        return not self.verEQ(other)
    def verLT(self, other):
        """ Uses verCMP, tests if our _rpm-version_ is <  other. """
        return self.verCMP(other) <  0
    def verLE(self, other):
        """ Uses verCMP, tests if our _rpm-version_ is <= other. """
        return self.verCMP(other) <= 0
    def verGT(self, other):
        """ Uses verCMP, tests if our _rpm-version_ is >  other. """
        return self.verCMP(other) >  0
    def verGE(self, other):
        """ Uses verCMP, tests if our _rpm-version_ is >= other. """
        return self.verCMP(other) >= 0

    @property
    def ui_envr(self):
        if self.epoch == '0':
            return self.nvr
        else:
            return self.envr
    @property
    def ui_envra(self):
        if self.epoch == '0':
            return self.nvra
        else:
            return self.envra
    @property
    def ui_nevr(self):
        if self.epoch == '0':
            return self.nvr
        else:
            return self.nevr
    @property
    def ui_nevra(self):
        if self.epoch == '0':
            return self.nvra
        else:
            return self.nevra

    @property
    def ui_evr(self):
        if self.epoch == '0':
            return self.vr
        else:
            return self.evr
    @property
    def ui_evra(self):
        if self.epoch == '0':
            return self.vra
        else:
            return self.evra

    @property
    def envr(self):
        return '%s:%s' % (self.epoch, self.nvr)
    @property
    def envra(self):
        return '%s:%s' % (self.epoch, self.nvra)
    @property
    def evr(self):
        return '%s:%s' % (self.epoch, self.vr)
    @property
    def evra(self):
        return '%s:%s' % (self.epoch, self.vra)

    @property
    def na(self):
        return '%s.%s' % (self.name, self.arch)

    @property
    def nv(self):
        return '%s-%s' % (self.name, self.version)
    @property
    def nvr(self):
        return '%s-%s' % (self.name, self.vr)
    @property
    def nvra(self):
        return '%s-%s' % (self.name, self.vra)
    @property
    def nevr(self):
        return '%s-%s' % (self.name, self.evr)
    @property
    def nevra(self):
        return '%s-%s' % (self.name, self.evra)

    @property
    def vr(self):
        return '%s-%s' % (self.version, self.release)
    @property
    def vra(self):
        return '%s-%s.%s' % (self.version, self.release, self.arch)

# Koji API likes to represent epoch with ints and None if rpm has None, sigh.
def epochnum2epoch(epochnum):
    if epochnum is None:
        return '0'
    return str(epochnum)
def epoch2epochnum(epoch):
    if epoch == '0': # Bad, sigh. Sometimes, but not often, actually int('0')
        return None
    return int(epoch)


def nvr2pkg(nvr, arch=None, epoch=None):
    n, v, r = nvr.rsplit('-', 2)
    return Pkg(n, v, r, arch, epoch)

def nvra2pkg(nvra, epoch=None):
    nvr, a = nvra.rsplit('.', 1)
    pkg = nvr2pkg(nvr, a, epoch)
    return pkg

def nevra2pkg(nevra):
    n, ev, ra = nevra.rsplit('-', 2)
    if ':' in ev:
       e, v = ev.split(':', 1)
    else:
       e, v = '0', ev
    r, a = ra.rsplit('.', 1)
    return Pkg(n, v, r, a, e)

def srpm2pkg(srpm):
    if srpm.endswith(".rpm"):
        srpm = srpm[:-len(".rpm")]
    return nvra2pkg(srpm)


def returnNewestByName(pkgs, single=True): # YUM API, kinda
    """return list of newest packages based on name matching
       this means(in name.arch form): foo.i386 and foo.noarch will
       be compared to each other for highest version."""

    highdict = {}

    for pkg in pkgs:
        if pkg.name not in highdict:
            highdict[pkg.name] = [pkg]
            continue
        pkg2 = highdict[pkg.name][0]
        if pkg.verGT(pkg2):
            highdict[pkg.name] = [pkg]
        if single or pkg.verLT(pkg2):
            continue
        highdict[pkg.name].append(pkg)

    #this is a list of lists - break it back out into a single list
    returnlist = []
    for polst in highdict.values():
        for po in polst:
            returnlist.append(po)

    return returnlist

def returnNewestByNameArch(pkgs, single=True): # YUM API, kinda
    """return list of newest packages based on name, arch matching
        this means(in name.arch form): foo.i386 and foo.noarch are not 
        compared to each other for highest version only foo.i386 and 
        foo.i386 will be compared
        Note that given: foo-1.i386; foo-2.i386 and foo-3.x86_64
        The last _two_ pkgs will be returned, not just one of them. """

    highdict = {}

    for pkg in pkgs:
        na = (pkg.name, pkg.arch)
        if na not in highdict:
            highdict[na] = [pkg]
            continue
        pkg2 = highdict[na][0]
        if pkg.verGT(pkg2):
            highdict[na] = [pkg]
        if single or pkg.verLT(pkg2):
            continue
        highdict[na].append(pkg)

    #this is a list of lists - break it back out into a single list
    returnlist = []
    for polst in highdict.values():
        for po in polst:
            returnlist.append(po)

    return returnlist

# Similar to matchPackageNames() in yum, but smaller/simpler.
def match_pkgs(args, bpkgs):
    ret = []
    for bpkg in sorted(bpkgs):
        full = (bpkg.name, bpkg.nv, bpkg.nvr, bpkg.nvra)
        found = len(args) == 0
        for arg in sorted(args):
            if found:
                break
            if arg in full:
                found = True
        for arg in sorted(args):
            if found:
                break
            for m in full:
                if fnmatch.fnmatch(m, arg):
                    found = True
                    break
        if not found:
            continue
        ret.append(bpkg)
    return ret


def _is_branch_el8(pkg):
    """ Is this a branch el8 pacakge. Eg. foo-1-2.el8_3.noarch """
    return 'el8_' in pkg.release

def _is_module(pkg):
    """ Is this a module pacakge. Eg. foo-1-2.module+el8.1.0+2940+f62455ee.noarch """
    return '.module+' in pkg.release

def _is_rebuild(pkg):
    """ Is this a rebuild pacakge. Eg. foo-1-2.el8+4.noarch """
    rel = pkg.release
    nums = "0123456789"
    if rel[-1] not in nums:
        return False
    while rel and rel[-1] in nums:
        rel = rel[:-1]
    if rel and rel[-1] == '+':
        return True
    return False
