import numpy
import string, inspect, re, fnmatch, pandas
from collections import Iterable, namedtuple, OrderedDict, deque

class Rep(OrderedDict):
    """
    This serves as a base class for the different magnetic and structure representation formalisms.
    """
    def __init__(self):
        """"""
        super(Rep,self).__init__()
        return


class BasisVector(numpy.ndarray):
    """
    TODO:
    <done> Extends ndarray (see: http://docs.scipy.org/doc/numpy/user/basics.subclassing.html) 
    """
    def __new__(bv, input_array, d=None, Nbv=None, Nrep=None, Natom=None, Nunique_atom=None, norm=False):
        # Input array is an already formed ndarray instance, but we want to normalize it
        if norm:
            norm_fac = numpy.linalg.norm(input_array)
            if norm_fac > 0.:
                input_array = input_array / norm_fac
            #print input_array
        # Then cast to be our class type        
        obj = numpy.asanyarray(input_array).view(bv)
        # add the new attribute to the created instance
        obj.d = d
        obj.Nbv = Nbv
        obj.Nrep = Nrep
        obj.Natom = Natom   
        obj.Nunique_atom = Nunique_atom
        obj.name = 'atom'+str(Natom)+'_'+str(Nunique_atom)
        # Finally, we must return the newly created object:
        return obj  
    
    def __array_finalize__(self,obj):
        """
        TODO:
        * Should raise a better error
        """
        if obj is None: return
        if not (obj.shape == (3,)): raise TypeError("The input array is of the wrong shape.")
        for name in ['d', 'Nbv', 'Nrep', 'Nmagatom', 'name']:
            setattr(self, name, getattr(obj, name, None))
        return


class BasisVectorGroup(OrderedDict):
    """
    BasisVectorGroups are composed of all BasisVectors for equivalent atoms produced by a single Rep. 
    For the full set of BasisVectors for a single atom including contributions from all Reps (and qm), use a BasisVectorCollection.
    Test
    """    

    key = None

    def __init__(self, basisvectors=[], Nbv=1, Nunique_atom=1, names=None, orbit=None, Nirrep=0):
        """
        Nbv should be given by the Order of the Irrep times the number of Copies.
        I decided not to have the option to input a BasisVectorGroup directly. It is simple to make a list of BasisVectors.
        TODO:
        """       
        OrderedDict.__init__(self)
        self.Nirrep = Nirrep
        #assert isinstance(IR, Irrep)
        #self.IR = IR
        #super(BasisVectorGroup, self).__init__()
        # Set the coefficient to a default value:
        self.name = 'psi'+str(Nbv)+'_'+str(Nunique_atom)
        self.setBasisVectors(basisvectors)
        self.set_key()
        
        return    

    def setBasisVectors(self, basisvectors):
        """"""
        basisvectors = list(basisvectors)
        for basisvector in basisvectors:
            self[basisvector.name] = basisvector  
        self.setCoeff()
        return

    def setCoeff(self, coeff=1.+1j*0.):
        """
        """
        self.coeff = coeff
        return

    def addBasisVector(self, basisvector):
        """
        TODO:
        * Check for the precense of that basisvector already
        """
        self[basisvector.name] = basisvector
        # set a coeff
        return

    def getMagneticMoment(self, d):
        """
        DEPRECATED
        """
        m = numpy.asanyarray([0.,0.,0.], dtype=numpy.complex_)
        for bv in list(self.values()):
            if numpy.isclose(d,bv.d).all():
                m += bv
        return m

    def set_key(self):
        G = 'G'+str(self.Nirrep)
        bvg = self.name
        self.key = G+'_'+bvg


    def checkBasisVectors(self):
        # Perform some checks to make sure the objects are what we think they are
        assert(isinstance(self.basisvectors, list))
        
        # Composed of BasisVectors
        for basisvector in self.basisvectors:
            assert(isinstance(basisvector, BasisVector))
            
        # For the same atom
        testbv = self.basisvectors[0]
        for basisvector in self.basisvectors:
            assert(testbv.d == basisvector.d)  
        return


class BasisVectorCollection(OrderedDict):
    """
    A BasisVectorCollection is a collection of BasisVectorGroups from different Reps but corresponding to the same atom. 
    It is broken up into named fields corresponding to each of the ordering wavevectors.
    """

    meta = {}

    def __init__(self, *args, **kwargs):
        """
        TODO:
        """
        bvgs = []
        for arg in args:
            assert(isinstance(arg, BasisVectorGroup))
            bvgs.append((arg.key, arg))

        OrderedDict.__init__(self, bvgs)
        self._overrides(**kwargs)
        self.order = len(self)
        self._setCoeffs()
        self._setLinCombs()
        self._setMeta()

    def _overrides(self, **kwargs):
        for kw,val in kwargs.items():
            try:
                setattr(self, kw, val)
            except AttributeError:
                raise

    def _setMeta(self):
        d = []
        for bvtup in self.bvs:
            d.append(bvtup[0].d)
        self.meta['d'] = tuple(d)

    def _setCoeffs(self, coeffs=None):
        if coeffs:
            assert(len(coeffs) == self.order)
            self.coeffs = numpy.asarray(coeffs, dtype=numpy.complex_).squeeze()
        else:
            coeffs = tuple(self.order*[1+0j])
            self.coeffs = numpy.asarray(coeffs, dtype=numpy.complex_).squeeze()

    def _setLinCombs(self, **kwargs):
        bvs = tuple(zip(*map(OrderedDict.values, self.values())))
        for bv in bvs:
            assert(len(bv) == self.order)
        self.bvs = bvs

        _tmp_bv = numpy.asarray(self.bvs)
        _tmp_bv = numpy.einsum('j, ijk -> ijk', self.coeffs, _tmp_bv)
        self.lincombs = numpy.sum(_tmp_bv, axis=1)

    def update(self, *coeffs):
        self._setCoeffs(coeffs=coeffs)
        self._setLinCombs()

    def getMagneticMoment(self, d):
        m = numpy.asanyarray([0.,0.,0.], dtype=numpy.complex_)
        lidx = numpy.isclose(d, numpy.asarray(self.meta['d'])).all(axis=1)
        return self.lincombs[lidx,...]


class Irrep(OrderedDict):
    """
    An Irrep class is composed of BasisVectorGroups corresponding to each atomic site in the compound.
    It contains identifying information for the Irrep in Kovalev notation.
    ...
    ----------
    Attributes:
    ...
    ----------
    TODO:
    <done> Moved frac_coords to within each BasisVector itself
    * Access the different atomic sites by a named field (namedtuple)
    """
    def __init__(self, qm=None, sg=None, N=None, Natoms=None, copies=None, order=None, bvg=None):
        """
        This will create an object to control the irrep and basis vectors from Sarah (or elsewhere) used for fitting the magnetic structure.
        TODO:
        * Long term, it would be nice if all the input here could be pulled from Sarah output. Certainly possible, but would take some careful work.
        """
        OrderedDict.__init__(self)
        # Set irrep number, how many copies present, and its order
        self.N      = N
        self.copies = copies
        self.order  = order        
        
        # Set the total number of basis vectors groups and atoms for this irrep
        self.bvg   = bvg
        self.Natoms = Natoms
        
        # Set the name of the irrep
        self.setName()
        
        # Set a flag for tracking whether all the basis vectors have been added.
        # Eventually want a more elegant way of doing this
        self.defined= False
        
        return

    def setName(self, name=None):
        """"""
        if name is not None:
            self.name = name
        else:
            self.name = 'G'+str(self.N)
        return

    def addBasisVectorGroup(self, frac_coord, psi):
        """"""
        
        self.psis
        return

    def getBasisVectorGroup(self, atom):
        """
        """
        return

    def checkIrrep(self):
        """
        TODO: 
        * Implement all the checks required to make sure the Irrep is sound.
        """
        assert(len(bvg) == Natoms)
        # ...
        return

    def __add__(self, other):
        """"""
        return Corep([self, other])
    def __eq__(self, other):
        """"""
        return self.N == other.N

    def __repr__(self):
        return repr(self.name)

    def __str__(self):
        return str(self.copies)+'$\Gamma_{'+str(self.N)+'}^{'+str(self.order)+'}'


class Corep(Irrep):
    """
    A Corep class combines two or more Irreps into a single Corep which otherwise behaves just the same way. The net effect is to increase the size of the constituitive BasisVectorGroups.
    ...
    ----------
    Additional Attributes:
    ...
    ----------
    TODO:
    * 
    """
    def __init__(self, irreps):
        
        return


class MSG(Rep):
    """
    This is a Magnetic Space Group object.
    ...
    ----------
    Attributes:
    ...
    ----------
    TODO:
    * So far from being ready.
    """
    def __init__(self):    
        
        return NotImplemented


class RepGroup(OrderedDict):
    """
    > NOTE: This is a MUTEABLE type.
    TODO:
    
    * Will be the base class for MagRepGroup (and others) and may be able to replace them altogether... (later)
    <done> Implemented as a subclass of OrderedDict.
        * May want to edit the __getitem___ method so that its returns RepGroup[key-1]. That way irreps, etc. can be referenced by number as well. 
    """
    def __init__(self, reps=None, crystal=None, repcollection=None, basisvectorgroup=None, **kwargs):
        """
        TODO:
        * Add ability to input reps as a list and pull the names for dictionary labels
        """
        self.setFamilyName()
        super(RepGroup, self).__init__()
        
        self.basisvectorgroup = basisvectorgroup
        self.bvg = self.basisvectorgroup # alias
        self.setRepCollection(repcollection, rcname=kwargs['rcname'])
            
        # Ready the input
        self.setReps(reps) # also claims reps as children
        return

    def setFamilyName(self, name='repgroup'):
        self.familyname = name   
        return

    def setRepCollection(self, repcollection, name='repcollection'):
        """"""
        if repcollection is not None:
            if not hasattr(repcollection, RepCollection): raise TypeError ('The repcollection field is for a RepCollection type object (or subclass).')
            setattr(self, name, repcollection)
        else:
            setattr(self, name, repcollection)
        return

    def setReps(self, reps):
        """"""
        if reps is None: pass
        elif not isinstance(reps, Iterable): reps = list(reps)
        else:
            for rep in reps:
                if not isinstance(rep, Rep): raise TypeError('The reps variable should be a Reps instance or subclass.')
                self[rep.name] = rep
                rep.setParents(self, child=rep)
                
        # Also set access to dict values by attribute
        for rep in self:
            setattr(self, rep.name, rep)
        return

    def getBasisVectorCollection(self, d):
        """
        This function will return the BasisVectorCollection object corresponding to the set of BasisVectors at a particular magnetic site.
        """
        return

    def setParents(self, parents, **kwargs):
        """
        This method sets the parent reference of NuclearStructures to a Cystal and returns an AssertionError if the parent is of the wrong type
        """    
        errmsg = 'RepGroups expect a Crystal or RepCollection object as parent. Plase give an appropiate object to reference.'
        errmsg = kwargs['errmsg'] if 'errmsg' in kwargs else errmsg
        
        types  = (RepCollection, Crystal)
        types  = kwargs['types'] if 'types'  in kwargs else types
        
        if hasattr(parents, '__iter__'):
            for parent in parents: 
                if parent is None: pass
                elif not isinstance(parent, types): raise TypeError(errmsg) 
                else: setattr(self, parent.familyname, parent)
                parent.setChild(self)
        else:
            self.setParents([parents], errmsg=errmsg, types=types)        
        return

    def claimChildren(self, family = ['basisvectorcollection', 'basisvectorgroup'], child=None):
        """
        This is performed in the init stage so that all consitituents of the Nuclear Structure may back-refernece it by name.
        TODO:
        * Perhaps this is modified to include AtomGroups and/or to replace atoms with an AtomGroup
        * Need to include checks here that say whether the Child is of the right type. (Somewhat redundant as it is handled by the Child as well.)
        """
        if child is None:
            for each_child in self:
                each_child.setParents(self)
        else:
            child.setParents(self)
        
        attr = getFamilyAttributes(self, family)
        for a in attr:
            label, child = a
            if child is not None: child.setParent(self)        
        return 


class NucRepGroup(RepGroup):
    """
    TODO:
    * For implementing structural distortions
    """
    pass


class MagRepGroup(OrderedDict):
    """
    A MagRep class is a collection of Reps (MSG, Irrep, Corep, etc.) for magnetic order in a given system.
    There are the same number of Reps as there are ordering wavevectors, qm. 
    The fitting can be performed for any combination of those wavevectors and their corresponding Reps.
     ...
    ----------
    Additional Attributes:
    ...
    ----------
    TODO:
    * Long term, the idea is to incorporate the option to use magnetic spacegroups (MSGs) as well
    * Long term, it would be nice if this could be read directly from Sarah. Should be quite doable.
    ** Even more ideally, porting the functionality of Sarah and/or Bilbao to Python would be FANTASTIC. (See pycrystfml: in-progress...)
    
    """
    def __init__(self, reps=None, crystal=None, repcollection=None, sarahfile=None, basisvectorgroup=None, bvgs=[], **kwargs):
        """
        Need to fix class relations...
        """
        self.setFamilyName()
        OrderedDict.__init__(self)
        
        self.IR0 = None
        self.bv0 = 0
        self.bvgs = bvgs
        self.basisvectorgroup = basisvectorgroup
        self.bvg = self.basisvectorgroup # alias
        self.bvcs = []
        self.bvc  = None
        #self._populateCollections()
        self.setRepCollection(repcollection, rcname='magrepcollection')
            
        # Ready the input
        self.setReps(reps) # also claims reps as children      
        #super(MagRepGroup, self).__init__(reps=reps, crystal=crystal, repcollection=repcollection, rcname='magrepcollection')
        self.mrc = self.magrepcollection
        if sarahfile is not None: 
            self.readSarahSummary(sarahfile)
        return

    def setReps(self, reps):
        """"""
        if reps is None: pass
        elif not isinstance(reps, Iterable): reps = list(reps)
        else:
            for rep in reps:
                if not isinstance(rep, Rep): raise TypeError('The reps variable should be a Reps instance or subclass.')
                self[rep.name] = rep
                rep.setParents(self, child=rep)
                
        # Also set access to dict values by attribute
        for rep in self:
            setattr(self, rep.name, rep)
        return

    def setRepCollection(self, repcollection, rcname='magrepcollection'):
        """
        TODO:
        * Should implement with super()...
        """
        if repcollection is not None:
            if not hasattr(repcollection, MagRepCollection): raise TypeError ('The repcollection field in a MagRepGroup is for a MagRepCollection type object.')
            setattr(self, rcname, repcollection)
        else:
            setattr(self, rcname, repcollection)
        return

    def _populateCollections(self):
        raise NotImplementedError

    def addBasisVector(self, bv, Nrep=None, Nbv=0, Nunique_atom=None, Natom=None, Nirrep=None):
        """
        TODO:
        * Needs to be finished passing on and correlating the information...
        """
        #if 'G'+str(Nirrep) in self.keys():
        if Nrep:
            pass
        if Nirrep:
            Nrep = Nirrep
            print('use `Nrep=value` instead of `Nirrep`. the later is depricated.')

        self['G'+str(Nrep)]['psi'+str(Nbv)+'_'+str(Nunique_atom)].addBasisVector(bv)
        
        return

    def getBasisVector(self, Nrep=None, Nbv=None, Nunique=1, Nat=1):
        if Nrep is None:
            Nrep = self.IR0
        if Nbv is None:
            Nbv = self.bv0
        bv = self['G'+str(Nrep)]['psi'+str(Nbv)+'_'+str(Nunique)]['atom'+str(Nat)+'_'+str(Nunique)]
        return bv

    def sarah2pyRep(self, lines, lid=None, **kwargs):
        """"""
        #line = str(line)
        if lid is None: raise TypeError('Please provide an identifier for the line to select the proper algorithm for translation')
        
        if lid == 'ATOM-IR':
            """
            Return the value of the basis vector and the atom number
            """
            
            Natom, _0, bv = lines.partition(':')
        
            # The atom number is:
            Natom = int(re.findall(r'\d+', str(Natom))[0])
            
            bvr, _0, bvi = bv.partition('+') 
            bvr = numpy.asanyarray([float(i) for i in re.findall( r'[-+]?\d*\.\d+|\d+',bvr)])
            bvi = numpy.asanyarray([float(i) for i in re.findall( r'[-+]?\d*\.\d+|\d+',bvi)])
            
            # The basis vector is:
            bv = bvr + 1j*bvi
            
            return  bv, Natom
        #
        elif lid == 'VECTOR':
            _0, _1, qm = lines.partition('=')
            qm = numpy.asanyarray([float(i) for i in re.findall(r'[+,-]?\d+', qm)])            
            return qm
        #
        elif lid == 'N-O':            
            start = lines.index('ORDERS OF THE REPRESENTATIONS:')+1
            stop  = lines.index('APPLICATION OF ANTIUNITARY THEORY LEADS TO THE FOLLOWING COREPRESENTATIONS:') 
            deq   = deque(lines[start:stop])
            lines[:stop] = []
            
            Nirreps = []
            Oirreps = []
            while len(deq) is not 0:
                Nirrep, _1, Oirrep = deq.popleft().partition(':')
                Nirrep = int(Nirrep)
                Oirrep = int(Oirrep)
                Nirreps.append(Nirrep)
                Oirreps.append(Oirrep)
                self['G'+str(Nirrep)] = Irrep(qm=self.qm, sg=None, N=Nirrep, Natoms=None, 
                                        copies=None, 
                                        order=Oirrep, 
                                        bvg=None)            
            return Nirreps, Oirreps
        #
        elif lid =='COREP':
            self.hasCorep = False
            start = lines.index('APPLICATION OF ANTIUNITARY THEORY LEADS TO THE FOLLOWING COREPRESENTATIONS:') + 2
            stop  = lines.index('COORDINATES OF PRINCIPAL ATOMS:')
            deq   = deque(lines[start:stop])
            
            Crs = []; Irs = []; Os = []
            foundAll = False
            while not foundAll:
                l = deq.popleft()
                _0, _1, l = l.partition(')')
                
                if len(l) > 0:
                    # Get the Corep symbol
                    Cr = str(re.findall('[ABC]', l))
                    Crs.append(Cr)
                    
                    # Get the Irreps order and numbers contributing to each Corep
                    O, Ir1, Ir2 = re.findall(r'\d+', l)
                    Os.append(O)
                    Irs.append((int(Ir1),int(Ir2)))
                
                # Check if all the Irreps are represented
                found = True
                foundIrreps = list(numpy.asanyarray(Irs).flatten())
                for Nirrep in self.Nirreps:
                    found *= (Nirrep in foundIrreps)
                foundAll = found  
                
            if 'C' in Crs: self.hasCoreps = True
            return Crs, Os, Irs
        #
        elif lid == 'COORDS':
            Nunique_a = kwargs['Nunique_a']
            Natoms = 0; ds = {}
            for l in lines:
                Natom, _0, d = l.partition(':')
                
                # Grab the atom number
                Natom = int(re.findall(r'\d+', Natom)[0])
                Natoms = max(Natom, Natoms)
                #print Natom
                
                # Grab the coordinate of the atom
                dx, dy, dz = tuple(re.findall(r'[.]?\d+', d))
                ds[str(Natom)+'_'+str(Nunique_a)] = numpy.asanyarray([float(dx),float(dy),float(dz)])   
            return ds, Natoms

    def readSarahSummary(self, filename):
        """
        Definitely not most efficient, but quick and dirty
        """
        # Get the data just as a list of strings for each line
        data = pandas.read_table(filename)
        lines = []
        for l in list(data.values[:][:]):
            lines.append(str(l[0])) 
        for l in lines:
            lines[lines.index(l)] = str(l)        
            
        # Get the descriptive information by reading the beginning lines
        # Read in the ordering wavevector, qm:
        self.qm = self.sarah2pyRep(fnmatch.filter(lines, 'VECTOR K*=*')[0], lid='VECTOR')        
        
        # Get a list of Irreps and their orders, while also making those Irreps in the MagRepGroup along the way.   
        Nirreps, Oirreps = self.sarah2pyRep(lines, lid='N-O')
        self.Nirreps = Nirreps
            
        # The total number of Irreps is determined as:
        self.Nreps = len(self.Nirreps)
                
        # Now get information regarding any possible Correps
        Crs, Os, Irs = self.sarah2pyRep(lines, lid='COREP')
        
        # Find out how many distinct atoms (orbits) are generated. This sets the number of BasisVectorGroups
        # can do a fnmatch.filter for 'ORBITS ARE PRESENT' if you wish
        idx_unique_atoms = []
        for l in fnmatch.filter(lines, 'ANALYSIS FOR ATOM*'):
            ## Get the atom names here too.
            idx_unique_atoms.append(lines.index(l)+2)
            
        #idx_unique_atoms[-1] = len(lines)
        #idx_unique_atoms = [m.start() for m in re.compile(re.escape(lines)).finditer('ANALYSIS FOR ATOM*')]
                        
        # Get the indicies for the coordiantes to end the substring used to extract the positions of the atoms
        idx_coords_stop = []; i=0
        for l in fnmatch.filter(lines, 'DECOMPOSITION OF THE MAGNETIC REPRESENTATION INTO IRs OF Gk:'):
            """
            *!! FIX !!*
            """        
            idx_coords_stop.append(lines.index(l, idx_unique_atoms[i]))
            i+=1            
            
        a_start = idx_unique_atoms[0]
        for a_stop in idx_unique_atoms[1:]+[-1]:
            
            a_lines = lines[a_start:a_stop]
            Nunique_a = idx_unique_atoms.index(a_start)+1
            #print Nunique_a
            
            # Get the atomic positions as a dict labeled by the atom number
            # eventually NEED to check against the CIF for atom labels or make sure that they are adjusted according to the fractional coordinates.
            ds, Natoms = self.sarah2pyRep(lines[a_start:idx_coords_stop[idx_unique_atoms.index(a_start)]], lid='COORDS', Nunique_a=Nunique_a)

            # Search for the lines beginning the Irreps so as to later get the BasisVectors from them
            subl_irrep = deque(fnmatch.filter(a_lines, 'IR #*, BASIS VECTOR: #*(ABSOLUTE NUMBER:#*)'))
            # This starts each BVG then find all the atom lines between this and the '******' line to add to a single basis vector number (Nbv)
            
            while len(subl_irrep) is not 0:
                """
                TODO:
                * Handle flags for when to increase the Atom#, etc. in this loop through the file so we know where to look for the fractional coordiantes.
                """
                # Grab the string for each Irrep-BasisVector pair
                l = subl_irrep.popleft()
                #print l
                
                # Parse the Irrep and BasisVector number from the line
                Nirrep, Nbv, Nbv_abs = [int(s) for s in re.findall(r'\d+', l)]  
                
                # Add a BasisVectorGroup to the Irrep for each set of atoms sharing a basis vector
                self['G'+str(Nirrep)]['psi'+str(Nbv)+'_'+str(Nunique_a)] = BasisVectorGroup(basisvectors=[], 
                                                        Nbv=Nbv, Nunique_atom=Nunique_a,
                                                        names=None, 
                                                        orbit=None)
                
                # Grab the index of the lines for each atom's basis vectors in the current group and combine into deque
                start = lines.index(l)+1
                stop  = start + Natoms+1 # need to handle the setting of Natoms
                deq = deque(lines[start:stop])
                
                # Go through the deque and add the basis vector values to the MagRepGroup
                while len(deq) is not 0:
                    line = deq.popleft()
                    #print line
                    if ('*' not in line) and ('#' not in line):
                        bv, Natom = self.sarah2pyRep(line, lid='ATOM-IR')
                        assert(Natom <= Natoms)
                        bv = BasisVector(bv, d=ds[str(Natom)+'_'+str(Nunique_a)], Nbv=Nbv, Nrep=Nirrep, Natom=Natom, Nunique_atom=Nunique_a)
                        self.addBasisVector(bv, Nirrep, Nbv, Nunique_a, Natom)
                    else:
                        pass
            
            a_start = a_stop
        
        if self.hasCorep:
            """
            Need to restructure the MRG to have Coreps. 
            This is actually easier than it sounds because we can just ignore the Irreps making up the Coreps or force their coefficients to vary together.
            """
            # Make correps
            #self
            pass
        return

    def bas2rep(self, fp, bsr, lid=None, **kwargs):
        """"""
        if lid == 'N-O':
            for l in bsr:
                if "=> Dimensions of Ir(reps):" in l:
                    s = l.strip()
                    print(s)
                    break
            dims = list(map(int, list(s.partition(':')[-1].replace(" ", ""))))
            print(dims)

            for l in bsr:
                if "-> GAMMA(Magnetic):" in l:
                    decomp_string = l.replace(" ","")
                    print(decomp_string)

            Nirreps = []
            Oirreps = []
            ct = 0
            for dim in dims:
                ct += 1
                if "("+str(ct)+")" in decomp_string:
                    Oirreps.append(dim)
                    Nirreps.append(ct)
                    self['G' + str(ct)] = Irrep(qm=self.qm, sg=None, N=ct, Natoms=None, copies=None,
                                                    order=dim, bvg=None)
            return Nirreps, Oirreps
        return

    def readBasIreps(self, magnetic):
        """
        Definitely not most efficient, but quick and dirty
        """

        # Get the descriptive information by reading the beginning lines
        # Read in the ordering wavevector, qm:
        self.qm = magnetic.qm

        fp  = magnetic.fp
        bsr = magnetic.bsr

        # Get a list of Irreps and their orders, while also making those Irreps in the MagRepGroup along the way.
        Nirreps, Oirreps = self.bas2rep(fp, bsr, lid='N-O')
        self.Nirreps = Nirreps

        # The total number of Irreps is determined as:
        self.Nreps = len(self.Nirreps)

        Nunique_a = 0
        for l in bsr:
            if "=> No. of sites:" in l:
                s = l.replace(" ", "")
                Nunique_a = int((s.partition(':')[-1]).strip("\n"))
                break

        ds = {}
        ct = 0
        for atom in magnetic.magatoms.values():
            ct += 1
            ds[str(ct)+"_"+str(Nunique_a)] = atom.d
        Natoms = ct

        lines = deque(fp)
        ct = 0
        nat = 0
        while len(lines) > 0:
            l=lines.popleft()
            if " ----- Block-of-lines for PCR start just below this line\n" in l:
                Nirrep = Nirreps[ct]
            if "BASR" in l:
                nat += 1
                #print(nat)
                r = [float(s) for s in re.findall(r'-?\d+\.*\d*', l)]
                l = lines.popleft()
                i = [float(s) for s in re.findall(r'-?\d+\.*\d*', l)]
                N = len(r) // 3
                assert len(i) // 3 == N
                #print(len(r))
                for q in range(N):
                    #print(q)
                    bv = numpy.array(r[3*q:3*(q+1)]) + 1j * numpy.array(i[3*q:3*(q+1)])
                    bv = BasisVector(bv, d=ds[str(nat) + '_' + str(Nunique_a)], Nbv=q, Nrep=Nirrep, Natom=nat,
                                 Nunique_atom=Nunique_a)
                    try:
                        self['G' + str(Nirrep)]['psi' + str(q) + '_' + str(Nunique_a)]
                    except KeyError:
                        self['G' + str(Nirrep)]['psi' + str(q) + '_' + str(Nunique_a)] = BasisVectorGroup(
                            basisvectors=[], Nbv=q, Nunique_atom=Nunique_a, names=None, orbit=None)
                    self.addBasisVector(bv, Nirrep, q, Nunique_a, nat)
            if " ----- End-of-block of lines for PCR \n" in l:
                ct += 1
                nat = 0
        return

    def setFamilyName(self, name='magrepgroup'):
        self.familyname = 'magrepgroup' 
        return

    def getMagneticMoment(self, d, Nrep=None, Nbv=None, Nunique=1):
        """"""
        if self.bvc:
            m = self.bvc.getMagneticMoment(d)
        else:
            if Nrep is None: Nrep = self.IR0
            if Nbv is None: Nbv = self.bv0
            bvg = list(self['G'+str(Nrep)].values())[Nbv]
            m = bvg.getMagneticMoment(d)
        return m

    def setBasisVectorCollection(self, basisvectorcollection=None):
        """"""
        self.basisvectorcollection = basisvectorcollection
        self.bvc = self.basisvectorcollection # alias
        return

    def setParents(self, parents):
        """"""
        errmsg = 'MagRepGroups expect a Crystal or MagRepCollection object as parent. Plase give an appropiate object to reference.'
        types = (MagRepCollection,Crystal)
        super(MagRepGroup, self).__setParents__(parents, errmsg=errmsg, types=types)
        return

    def claimChildren(self, family = ['basisvectorcollection', 'basisvectorgroup'], child=None):
        """
        This is performed in the init stage so that all consitituents of the Nuclear Structure may back-refernece it by name.
        TODO:
        * Perhaps this is modified to include AtomGroups and/or to replace atoms with an AtomGroup
        * Need to include checks here that say whether the Child is of the right type. (Somewhat redundant as it is handled by the Child as well.)
        """
        if child is None:
            for each_child in self:
                each_child.setParents(self)
        else:
            child.setParents(self)
        
        attr = getFamilyAttributes(self, family)
        for a in attr:
            label, child = a
            if child is not None: child.setParent(self)        
        return 


class RepCollection(OrderedDict):
    """
    > NOTE: This is a MUTEABLE type.
    TODO:
    * Decide if this is neccessary...
    """
    pass


class MagRepCollection(RepCollection):
    """"""
    pass


def getTrimmedAttributes(obj):
    """
    This function returns a list of attributes of the input object (class) as a list of tuples each of the form: ('field', <instance>)
    pulled from: http://stackoverflow.com/questions/9058305/getting-attributes-of-a-class
    """
    attributes = inspect.getmembers(obj, lambda a:not(inspect.isroutine(a)))
    return [a for a in attributes if not(a[0].startswith('__') and a[0].endswith('__'))]


def getFamilyAttributes(obj, family):
    """"""
    attr = getTrimmedAttributes(obj)
    attributes = []
    if family is not None:
        for fam in family:                    
            attributes.append(attr.pop(attr.index((fam, obj.__getattribute__(fam)))))            
    return attributes