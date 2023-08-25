import numpy as _numpy
import rebound as _rebound
import warnings as _warnings
from scipy.stats import uniform as _uniform
from .tools import *

try: from collections.abc import MutableMapping # Required for Python>=3.9
except: from collections import MutableMapping

class Star:
  '''
    This is the AIRBALL Star class.
    It encapsulates the relevant parameters for a given star.
    Only the mass is an quantity intrinsic to the object.
    The impact parameter, velocity, inclination, argument of periastron, and longitude of the ascending node quantities are defined with respect to the host star and plane passing through the star.
  '''
  def __init__(self, m, b, v, inc=None, omega=None, Omega=None, UNIT_SYSTEM=[], **kwargs) -> None:
    '''
    The Mass, m, (Msun), Impact Parameter, b, (AU), Velocity, v, (km/s)
    Inclination, inc, (rad), Argument of the Periastron, omega (rad), and Longitude of the Ascending Node, Omega, (rad)
    Or define an astropy.units system, i.e. UNIT_SYSTEM = [u.pc, u.Myr, u.solMass, u.rad, u.km/u.s].
    '''
    self.units = UnitSet(UNIT_SYSTEM)

    if inc == 'uniform' or inc == None: inc = 2.0*_numpy.pi * _uniform.rvs() - _numpy.pi
    if omega == 'uniform' or omega == None: omega = 2.0*_numpy.pi * _uniform.rvs() - _numpy.pi
    if Omega == 'uniform' or Omega == None: Omega = 2.0*_numpy.pi * _uniform.rvs() - _numpy.pi
    

    # Considering making it possible to specify the a,e, or q of the star, but I think it would be better to build tools to convert between the values instead.
    # a = kwargs.get('a', None)
    # e = kwargs.get('e', None)
    # q = kwargs.get('q', None)
    # sim = kwargs.get('sim', None)
    # if notNone([a,e,q]) and sim is None: raise AssertionError('Need to specify a simulation when initializing the perturbing star with orbital elements.')
    # if notNone([e,v]): raise AssertionError('Overdetermined. Specify either an eccentricity or a velocity for the perturbing star.')
    # if notNone([b,q]): raise AssertionError('Overdetermined. Specify either an impact parameter or a periastron for the perturbing star.')

    self.mass = m
    self.impact_parameter = b
    self.velocity = v
    self.inc = inc
    self.argument_periastron = omega
    self.longitude_ascending_node = Omega

  @property
  def UNIT_SYSTEM(self):
    return self.units.UNIT_SYSTEM

  @UNIT_SYSTEM.setter
  def UNIT_SYSTEM(self, UNIT_SYSTEM):
    self.units.UNIT_SYSTEM = UNIT_SYSTEM

  @property
  def m(self):
    return self._mass.to(self.units['mass'])

  @m.setter
  def m(self, value):
    self._mass = value.to(self.units['mass']) if isQuantity(value) else value * self.units['mass']

  @property
  def mass(self):
    return self.m

  @mass.setter
  def mass(self, value):
    self.m = value
  
  @property
  def b(self):
    return self._impact_parameter.to(self.units['length'])

  @b.setter
  def b(self, value):
    self._impact_parameter = value.to(self.units['length']) if isQuantity(value) else value * self.units['length']

  @property
  def impact_parameter(self):
    return self.b

  @impact_parameter.setter
  def impact_parameter(self, value):
    self.b = value

  @property
  def v(self):
    return self._velocity.to(self.units['velocity'])

  @v.setter
  def v(self, value):
    self._velocity = value.to(self.units['velocity']) if isQuantity(value) else value * self.units['velocity']

  @property
  def velocity(self):
    return self.v

  @velocity.setter
  def velocity(self, value):
    self.v = value

  @property
  def inc(self):
    return self._inclination.to(self.units['angle'])

  @inc.setter
  def inc(self, value):
    self._inclination = value.to(self.units['angle']) if isQuantity(value) else value * self.units['angle']

  @property
  def inclination(self):
    return self.inc

  @inc.setter
  def inclination(self, value):
    self.inc = value

  @property
  def omega(self):
    return self._argument_periastron.to(self.units['angle'])

  @omega.setter
  def omega(self, value):
    self._argument_periastron = value.to(self.units['angle']) if isQuantity(value) else value * self.units['angle']

  @property
  def argument_periastron(self):
    return self.omega

  @argument_periastron.setter
  def argument_periastron(self, value):
    self.omega = value

  @property
  def Omega(self):
    return self._longitude_ascending_node.to(self.units['angle'])

  @Omega.setter
  def Omega(self, value):
    self._longitude_ascending_node = value.to(self.units['angle']) if isQuantity(value) else value * self.units['angle']

  @property
  def longitude_ascending_node(self):
    return self.Omega

  @longitude_ascending_node.setter
  def longitude_ascending_node(self, value):
    self.Omega = value

  @property
  def params(self):
    return [self.m, self.b, self.v, self.inc, self.omega, self.Omega]
  
  @property
  def param_values(self):
    return _numpy.array([self.m.value, self.b.value, self.v.value, self.inc.value, self.omega.value, self.Omega.value])
  
  def q(self, sim):
    return star_q(sim, self)

  def stats(self, returned=False):
    ''' 
    Prints a summary of the current stats of the Star.
    '''
    s = f"<{self.__module__}.{type(self).__name__} object at {hex(id(self))}, "
    s += f"m= {self.mass:1.4g}, "
    s += f"b= {self.impact_parameter:1.4g}, "
    s += f"v= {self.velocity:1.4g}, "
    s += f"inc= {self.inc:1.4g}, "
    s += f"omega= {self.omega:1.4g}, "
    s += f"Omega= {self.Omega:1.4g}>"
    if returned: return s
    else: print(s)
  
  def __str__(self):
    return self.stats(returned=True)
  
  def __repr__(self):
    return self.stats(returned=True)
  
  def __len__(self):
    return -1


class Stars(MutableMapping):
  '''
    This class allows the user to access stars like an array using the star's index.
    Allows for negative indices and slicing.
    The implementation uses astropy.Quantity and numpy ndarrays and only generates a airball.Star object when a single Star is requested.
  '''
  def __init__(self, **kwargs) -> None:
    try: 
      self.units = UnitSet(kwargs['UNIT_SYSTEM'])
      del kwargs['UNIT_SYSTEM']
    except KeyError: self.units = UnitSet()

    try:
      # Check to see if was key is given.
      filename = kwargs['from_file']
      kwargs['m'], kwargs['b'], kwargs['v'], kwargs['inc'], kwargs['omega'], kwargs['Omega'] = _numpy.load(filename)
    except KeyError: pass
    except Exception as err: raise err

    self._Nstars = 0
    for key in kwargs:
      try: 
        len(kwargs[key])
        if isList(kwargs[key]) and len(kwargs[key]) > self.N:
          self._Nstars = len(kwargs[key])
      except: pass
    if 'size' in kwargs and self.N != 0: raise OverspecifiedParametersException('If lists are given then size cannot be specified.')
    elif 'size' in kwargs: self._Nstars = int(kwargs['size'])
    elif self.N == 0: raise UnspecifiedParameterException('If no lists are given then size must be specified.')
    else: pass

    
    try:
      # Check to see if was key is given.
      value = kwargs['m']
      # Check if length matches other key values.
      if len(value) != self.N: raise ListLengthException()
      # Length of value matches other key values, check if value is a list.
      elif isinstance(value, list):
        # Value is a list, try to turn list of Quantities into a ndarray Quantity.
        try: self._m = _numpy.array([v.to(self.units['mass']).value for v in value]) << self.units['mass']
        # Value was not a list of Quantities, turn list into ndarray and make a Quantity.
        except: self._m = _numpy.array(value) << self.units['mass']
      # Value was not a list, check to see if value is an ndarray.
      elif isinstance(value, _numpy.ndarray):
        # Assume ndarray is a Quantity and try to convert ndarray into given units.
        try: self._m = value.to(self.units['mass'])
        # ndarray is not a Quantity so turn ndarray into a Quantity.
        except: self._m = value << self.units['mass']
      # Value implements __len__, but is not a list or ndarray.
      else: raise IncompatibleListException()
    # This key is necessary and must be specified, raise and Exception.
    except KeyError: raise UnspecifiedParameterException('Mass, m, must be specified.')
    # Value is not a list, so assume it is an int or float and generate an ndarray of the given value.
    except TypeError: 
      value = value.to(self.units['mass']) if isQuantity(value) else value * self.units['mass']
      self._m = _numpy.ones(self.N) * value
    # Catch any additional Exceptions.
    except Exception as err: raise err


    try:
      # Check to see if was key is given.
      value = kwargs['b']
      # Check if length matches other key values.
      if len(value) != self.N: raise ListLengthException()
      # Length of value matches other key values, check if value is a list.
      elif isinstance(value, list):
        # Value is a list, try to turn list of Quantities into a ndarray Quantity.
        try: self._b = _numpy.array([v.to(self.units['length']).value for v in value]) * self.units['length']
        # Value was not a list of Quantities, turn list into ndarray and make a Quantity.
        except: self._b = _numpy.array(value) * self.units['length']
      # Value was not a list, check to see if value is an ndarray.
      elif isinstance(value, _numpy.ndarray):
        # Assume ndarray is a Quantity and try to convert ndarray into given units.
        try: self._b = value.to(self.units['length'])
        # ndarray is not a Quantity so turn ndarray into a Quantity.
        except: self._b = value * self.units['length']
      # Value implements __len__, but is not a list or ndarray.
      else: raise IncompatibleListException()
    # This key is necessary and must be specified, raise and Exception.
    except KeyError: raise UnspecifiedParameterException('Impact Parameter, b, must be specified.')
    # Value is not a list, so assume it is an int or float and generate an ndarray of the given value.
    except TypeError: 
      value = value.to(self.units['length']) if isQuantity(value) else value * self.units['length']
      self._b = _numpy.ones(self.N) * value
    # Catch any additional Exceptions.
    except Exception as err: raise err

    try:
      # Check to see if was key is given.
      value = kwargs['v']
      # Check if length matches other key values.
      if len(value) != self.N: raise ListLengthException()
      # Length of value matches other key values, check if value is a list.
      elif isinstance(value, list):
        # Value is a list, try to turn list of Quantities into a ndarray Quantity.
        try: self._v = _numpy.array([v.to(self.units['velocity']).value for v in value]) * self.units['velocity']
        # Value was not a list of Quantities, turn list into ndarray and make a Quantity.
        except: self._v = _numpy.array(value) * self.units['velocity']
      # Value was not a list, check to see if value is an ndarray.
      elif isinstance(value, _numpy.ndarray):
        # Assume ndarray is a Quantity and try to convert ndarray into given units.
        try: self._v = value.to(self.units['velocity'])
        # ndarray is not a Quantity so turn ndarray into a Quantity.
        except: self._v = value * self.units['velocity']
      # Value implements __len__, but is not a list or ndarray.
      else: raise IncompatibleListException()
    # This key is necessary and must be specified, raise and Exception.
    except KeyError: raise UnspecifiedParameterException('Velocity, v, must be specified.')
    # Value is not a list, so assume it is an int or float and generate an ndarray of the given value.
    except TypeError: 
      value = value.to(self.units['velocity']) if isQuantity(value) else value * self.units['velocity']
      self._v = _numpy.ones(self.N) * value
    # Catch any additional Exceptions.
    except Exception as err: raise err

    try:
      # Check to see if was key is given.
      value = kwargs['inc']
        # Check to see if value for key is string.
      if isinstance(value, str):
        # Value is a string, check to see if value for key is valid.
        if value != 'uniform': raise InvalidValueForKeyException()
        # Value 'uniform' for key is valid, now generate an array of values for key.
        self._inc = (2.0*_numpy.pi * _uniform.rvs(size=self.N) - _numpy.pi) * self.units['angle']
      # Value is not a string, check if length matches other key values.
      elif len(value) != self.N: raise ListLengthException()
      # Length of value matches other key values, check if value is a list.
      elif isinstance(value, list):
        # Value is a list, try to turn list of Quantities into a ndarray Quantity.
        try: self._inc = _numpy.array([v.to(self.units['angle']).value for v in value]) * self.units['angle']
        # Value was not a list of Quantities, turn list into ndarray and make a Quantity.
        except: self._inc = _numpy.array(value) * self.units['angle']
      # Value was not a list, check to see if value is an ndarray.
      elif isinstance(value, _numpy.ndarray):
        # Assume ndarray is a Quantity and try to convert ndarray into given units.
        try: self._inc = value.to(self.units['angle'])
        # ndarray is not a Quantity so turn ndarray into a Quantity.
        except: self._inc = value * self.units['angle']
      # Value implements __len__, but is not a list or ndarray.
      else: raise IncompatibleListException()
    # Key does not exist, assume the user wants an array of values to automatically be generated.
    except KeyError: self._inc = (2.0*_numpy.pi * _uniform.rvs(size=self.N) - _numpy.pi) * self.units['angle']
    # Value is not a list, so assume it is an int or float and generate an ndarray of the given value.
    except TypeError: 
      value = value.to(self.units['angle']) if isQuantity(value) else value * self.units['angle']
      self._inc = _numpy.ones(self.N) * value
    # Catch any additional Exceptions.
    except Exception as err: raise err

    try:
      # Check to see if was key is given.
      value = kwargs['omega']
        # Check to see if value for key is string.
      if isinstance(value, str):
        # Value is a string, check to see if value for key is valid.
        if value != 'uniform': raise InvalidValueForKeyException()
        # Value 'uniform' for key is valid, now generate an array of values for key.
        self._omega = (2.0*_numpy.pi * _uniform.rvs(size=self.N) - _numpy.pi) * self.units['angle']
      # Value is not a string, check if length matches other key values.
      elif len(value) != self.N: raise ListLengthException()
      # Length of value matches other key values, check if value is a list.
      elif isinstance(value, list):
        # Value is a list, try to turn list of Quantities into a ndarray Quantity.
        try: self._omega = _numpy.array([v.to(self.units['angle']).value for v in value]) * self.units['angle']
        # Value was not a list of Quantities, turn list into ndarray and make a Quantity.
        except: self._omega = _numpy.array(value) * self.units['angle']
      # Value was not a list, check to see if value is an ndarray.
      elif isinstance(value, _numpy.ndarray):
        # Assume ndarray is a Quantity and try to convert ndarray into given units.
        try: self._omega = value.to(self.units['angle'])
        # ndarray is not a Quantity so turn ndarray into a Quantity.
        except: self._omega = value * self.units['angle']
      # Value implements __len__, but is not a list or ndarray.
      else: raise IncompatibleListException()
    # Key does not exist, assume the user wants an array of values to automatically be generated.
    except KeyError: self._omega = (2.0*_numpy.pi * _uniform.rvs(size=self.N) - _numpy.pi) * self.units['angle']
    # Value is not a list, so assume it is an int or float and generate an ndarray of the given value.
    except TypeError: 
      value = value.to(self.units['angle']) if isQuantity(value) else value * self.units['angle']
      self._omega = _numpy.ones(self.N) * value
    # Catch any additional Exceptions.
    except Exception as err: raise err

    try:
      # Check to see if was key is given.
      value = kwargs['Omega']
        # Check to see if value for key is string.
      if isinstance(value, str):
        # Value is a string, check to see if value for key is valid.
        if value != 'uniform': raise InvalidValueForKeyException()
        # Value 'uniform' for key is valid, now generate an array of values for key.
        self._Omega = (2.0*_numpy.pi * _uniform.rvs(size=self.N) - _numpy.pi) * self.units['angle']
      # Value is not a string, check if length matches other key values.
      elif len(value) != self.N: raise ListLengthException()
      # Length of value matches other key values, check if value is a list.
      elif isinstance(value, list):
        # Value is a list, try to turn list of Quantities into a ndarray Quantity.
        try: self._Omega = _numpy.array([v.to(self.units['angle']).value for v in value]) * self.units['angle']
        # Value was not a list of Quantities, turn list into ndarray and make a Quantity.
        except: self._Omega = _numpy.array(value) * self.units['angle']
      # Value was not a list, check to see if value is an ndarray.
      elif isinstance(value, _numpy.ndarray):
        # Assume ndarray is a Quantity and try to convert ndarray into given units.
        try: self._Omega = value.to(self.units['angle'])
        # ndarray is not a Quantity so turn ndarray into a Quantity.
        except: self._Omega = value * self.units['angle']
      # Value implements __len__, but is not a list or ndarray.
      else: raise IncompatibleListException()
    # Key does not exist, assume the user wants an array of values to automatically be generated.
    except KeyError: self._Omega = (2.0*_numpy.pi * _uniform.rvs(size=self.N) - _numpy.pi) * self.units['angle']
    # Value is not a list, so assume it is an int or float and generate an ndarray of the given value.
    except TypeError: 
      value = value.to(self.units['angle']) if isQuantity(value) else value * self.units['angle']
      self._Omega = _numpy.ones(self.N) * value
    # Catch any additional Exceptions.
    except Exception as err: raise err
  
  @property
  def N(self):
    return self._Nstars
  
  @property
  def median_mass(self):
    return _numpy.median([mass.value for mass in self.m]) * self.units['mass']
  
  @property
  def mean_mass(self):
    return _numpy.mean([mass.value for mass in self.m]) * self.units['mass']
  
  def __getitem__(self, key):
    int_types = int, _numpy.integer
    
    if isinstance(key, slice):
        if key == slice(None, None, None): return self
        else: return Stars(m=self.m[key], b=self.b[key], v=self.v[key], inc=self.inc[key], omega=self.omega[key], Omega=self.Omega[key], UNIT_SYSTEM=self.units.UNIT_SYSTEM)

    if isinstance(key, int_types):
        # accept negative indices
        if key < 0: key += self.N
        if key < 0 or key >= self.N: raise AttributeError(f'Index {key} used to access stars out of range.')
        i = int(key)
        return Star(m=self.m[i], b=self.b[i], v=self.v[i], inc=self.inc[i], omega=self.omega[i], Omega=self.Omega[i], UNIT_SYSTEM=self.units.UNIT_SYSTEM)
    
    raise InvalidKeyException() 

  def __setitem__(self, key, value):
    star_type = Star, Stars
    if isinstance(value, star_type):
      self.m[key], self.b[key], self.v[key], self.inc[key], self.omega[key], self.Omega[key] = value.params
    else: raise InvalidStarException()
  
  def __delitem__(self, key):
    raise ValueError('Cannot delete Star elements from Stars array.')

  def __iter__(self):
    for i in range(self.N):
      yield Star(m=self.m[i], b=self.b[i], v=self.v[i], inc=self.inc[i], omega=self.omega[i], Omega=self.Omega[i], UNIT_SYSTEM=self.units.UNIT_SYSTEM)

  def __len__(self):
    return self.N
  
  def sortby(self, key, sim=None, argsort=False):
    '''
    Sort the Stars in ascending order by a defining parameter.

    m: mass
    b: impact parameter
    v: relative velocity at infinity
    inc: inclination
    omega: argument of the periastron
    Omega: longitude of the ascending node

    q: periapsis (requires REBOUND Simulation)
    e: eccentricity (requires REBOUND Simulation)

    The Stars can also be sorted arbitrarily by providing a list of indices of length N.
    By setting argsort=True the indices used to sort the Stars will be returned.
    '''

    inds = _numpy.arange(self.N)
    if key == 'm' or key == 'mass': inds = _numpy.argsort(self.m)
    elif key == 'b' or key == 'impact' or key == 'impact param' or key == 'impact parameter': inds = _numpy.argsort(self.b)
    elif key == 'v' or key == 'vinf' or key == 'v_inf' or key == 'velocity': inds = _numpy.argsort(self.v)
    elif key == 'inc' or key == 'inclination' or key == 'i' or key == 'I': inds = _numpy.argsort(self.inc)
    elif key == 'omega' or key == 'ω': inds = _numpy.argsort(self.omega)
    elif key == 'Omega' or key == 'Ω': inds = _numpy.argsort(self.Omega)
    elif key == 'q' or key == 'peri' or key == 'perihelion' or key == 'periastron' or key == 'periapsis': 
      if isinstance(sim, _rebound.Simulation):
        inds = _numpy.argsort(self.q(sim))
      else: raise InvalidParameterTypeException()
    elif key == 'e' or key == 'eccentricity': 
      if isinstance(sim, _rebound.Simulation):
        inds = _numpy.argsort(self.e(sim))
      else: raise InvalidParameterTypeException()
    elif isList(key): 
      if len(key) != self.N: raise ListLengthException()
      inds = _numpy.array(key)
    else: raise InvalidValueForKeyException()

    self.m[:] = self.m[inds]
    self.b[:] = self.b[inds]
    self.v[:] = self.v[inds]
    self.inc[:] = self.inc[inds]
    self.omega[:] = self.omega[inds]
    self.Omega[:] = self.Omega[inds]

    if argsort: return inds

  def save(self, filename):
    ''' Assumes default units... '''
    _warnings.warn("Assumes default units")
    data = self.param_values
    _numpy.save(filename, data)

  @property
  def m(self):
    return self._m

  @property
  def mass(self):
    return self.m
  
  @property
  def b(self):
    return self._b

  @property
  def impact_parameter(self):
    return self.b

  @property
  def v(self):
    return self._v

  @property
  def velocity(self):
    return self.v

  @property
  def inc(self):
    return self._inc

  @property
  def inclination(self):
    return self.inc

  @property
  def argument_periastron(self):
    return self.omega

  @property
  def omega(self):
    return self._omega

  @property
  def Omega(self):
    return self._Omega

  @property
  def longitude_ascending_node(self):
    return self.Omega

  @property
  def params(self):
    return [self.m, self.b, self.v, self.inc, self.omega, self.Omega]
  
  @property
  def param_values(self):
    return _numpy.array([self.m, self.b, self.v, self.inc, self.omega, self.Omega])
 
  def e(self, sim):
    sim_units = rebound_units(sim)
    G = (sim.G * sim_units['length']**3 / sim_units['mass'] / sim_units['time']**2)
    mu = G * (sim.calculate_com().m * sim_units['mass'] + self.m)

    numerator = self.b * self.v*self.v
    return _numpy.sqrt(1 + (numerator/mu)**2.)
  
  def q(self, sim):
    sim_units = rebound_units(sim)
    G = (sim.G * sim_units['length']**3 / sim_units['mass'] / sim_units['time']**2)
    mu = G * (sim.calculate_com().m * sim_units['mass'] + self.m)

    numerator = self.b * self.v*self.v
    star_e = _numpy.sqrt(1 + (numerator/mu)**2.)
    return self.b * _numpy.sqrt((star_e - 1.0)/(star_e + 1.0))


################################
###### Custom Exceptions #######
################################

class InvalidStarException(Exception):
  def __init__(self): super().__init__('Object is not a valid airball.Star object.')

class UnspecifiedParameterException(Exception):
  def __init__(self, message): super().__init__(message)

class OverspecifiedParametersException(Exception):
  def __init__(self, message): super().__init__(message)

class ListLengthException(Exception):
  def __init__(self): super().__init__('List arguments must be same length.')

class IncompatibleListException(Exception):
  def __init__(self): super().__init__('The given list type is not compatible. Please use a Python list or an ndarray.')

class InvalidValueForKeyException(Exception):
  def __init__(self): super().__init__('Invalid value for key.')

class InvalidParameterTypeException(Exception):
  def __init__(self): super().__init__('The given parameter value is not a valid type.')