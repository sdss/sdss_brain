# !/usr/bin/env python
# -*- coding: utf-8 -*-
#

import datetime
import tempfile
import json
import pathlib
import copy

from functools import wraps
from dataclasses import dataclass, field
from typing import TypeVar, Union
ProdModel = TypeVar('ProdModel', bound='ProductModel')
ModelType = TypeVar('ModelType', bound='Model')
ModelsType = TypeVar('ModelsType', bound='Models')

from datamodel_code_generator import generate
from pydantic import BaseModel

from sdss_brain import log
from sdss_brain.exceptions import BrainError
from sdss_brain.api.handler import ApiHandler
from sdss_brain.config import config

try:
    from datamodel.products import SDSSDataModel
except ImportError:
    SDSSDataModel = None


product_schema_path = pathlib.Path(__file__).parent / 'product_schema.py'


def check_schema_mod_time(days: int = 7, td: datetime.timedelta = None) -> bool:
    """ Checks the schema file modified time

    Checks the datamodel product schema file's last modified time
    to see if it's more than x days old (default is 7 days) from the
    current datetime.

    Parameters
    ----------
    days : int, optional
        the number of days to check against, by default 7
    td : datetime.timedelta, optional
        an optional timedelta object to use instead, by default None

    Returns
    -------
    bool
        True if file's lmt is more than x days old
    """
    modified = datetime.datetime.fromtimestamp(product_schema_path.stat().st_mtime)
    now = datetime.datetime.now()

    # get the timedelta and check the schema file last modified datetime
    td = td or datetime.timedelta(days=days)
    return (now - modified) < td



def create_product_schema(schema: dict):
    """ Create the datamodel product schema file

    Generates a "product_schema.py" python file containing
    the datamodel product model definitions as Python objects.  Uses the
    ``datamodel_code_generator`` package to generate Pydantic models
    of a JSON schema.  Writes the file to the directory of this module.

    Parameters
    ----------
    schema : dict
        a Pydantic schema model
    """
    # dump the schema JSON to a named temporary file
    with tempfile.NamedTemporaryFile(mode='w') as fp:
        fp.write(json.dumps(schema))
        fp.seek(0)
        # generate the product_schema python file
        generate(input_=pathlib.Path(fp.name), input_file_type='jsonschema',
                 output=product_schema_path, use_schema_description=True, field_include_all_keys=True)


def create_product_model(model: dict) -> ProdModel:
    """ Create a product model

    Instantiates a product model given the dictionary serialization
    of the datamodel.  For example, given the sdR.json datamodel file
    read into a Python dict, creates a Python model representation
    of its datamodel, based on the model schema.

    Parameters
    ----------
    model : dict
        A serialized representation of a datamodel product.

    Returns
    -------
    ProdModel
        a product model instance
    """
    if not product_schema_path.exists():
        log.warning('Product schema file does not exist. Run "create_product_schema" to generate it.')
        return

    # try to import the ProductModel from the product_schema.py file
    try:
        from sdss_brain.datamodel.product_schema import ProductModel
    except ModuleNotFoundError:
        log.warning('Cannot not import ProductModel from product_schema module.')
        return

    # if no model data return
    if not model:
        log.warning('No input model data provided.')
        return

    return ProductModel(**model)


def get_product_model(product: str, release: str = None, schema: bool = None) -> dict:
    """ Get a datamodel product or schema

    Get a datamodel product model using the Valis API.  If ``schema`` is set
    to True, then gets the model schema that defines the structure of all
    data models.

    Parameters
    ----------
    product : str
        the file species name of the datamodel
    release : str, optional
        the data release, by default None
    schema : bool, optional
        If True, gets the model schema instead, by default None

    Returns
    -------
    dict
        A serialized version of the datamodel product (or schema)
    """
    # construct the valis request path
    path = 'schema' if schema else 'products'
    url = f'info/{path}/{{product}}'

    # create a valis api handler
    a = ApiHandler(('valis', url, 'api'))

    # resolve the request url for the given product name
    a.resolve_url({'product': product})

    # send the request and get the response
    try:
        a.client.request(data={'release': release or config.release})
    except BrainError as ee:
        log.error(f'Error getting product model: {ee}')
        return
    else:
        return a.client.data


def generate_product_model(product: str, release: str = None, days: int = 7) -> ProdModel:
    """ Generate a new datamodel product object

    Generates a new Python object representation of a datamodel for a
    given file species.  If the schema definition does not exist or is out
    of date, it (re)creates it.

    Parameters
    ----------
    product : str
        the file species name of the datamodel product
    release : str, optional
        the data release, by default None
    days : int, optional
        the number of days to check the schema file against, by default 7

    Returns
    -------
    ProdModel
        a product model instance
    """
    # create or update the schema definition file
    if not product_schema_path.exists() or not check_schema_mod_time(days=days):
        if schema := get_product_model(product, release=release, schema=True):
            create_product_schema(schema)

    # generate the product object model
    model = get_product_model(product, release=release)
    return create_product_model(model)


def get_datamodel(product: str, release: str = None) -> ProdModel:
    """ Get a datamodel object

    Gets a datamodel as a python object for a given file species
    name.  Either gets the product model locally if the SDSS
    datamodel python package is installed, or remotely from the SDSS
    valis API.

    Parameters
    ----------
    product : str
        the file species name of the datamodel product
    release : str, optional
        the data release, by default None

    Returns
    -------
    ProdModel
        a product model instance
    """
    if SDSSDataModel:
        dm = SDSSDataModel()
        return None if product not in dm.products else dm.products[product]._model

    return generate_product_model(product, release=release)


def generate_product_list(release: str = None) -> list:
    """ Get a list of available SDSS datamodels

    Retrieves a list of SDSS datamodels for a given release
    from the SDSS valis API.

    Parameters
    ----------
    release : str, optional
        the data release, by default None

    Returns
    -------
    list
        a list of available datamodels
    """
    # build the url, create an API handler, and submit the request
    url = 'info/products'
    a = ApiHandler(('valis', url, 'api'))
    a.client.request(data={'release': release or config.release})
    return sorted(a.client.data['products']) if a.client.response.is_success else []


def list_datamodels(release: str = None) -> list:
    """ List the available datamodels

    Lists the available datamodels either locally if the
    SDSS datamodel python package is installed, or remotely
    from the SDSS valis API.

    Parameters
    ----------
    release : str, optional
        the data release, by default None

    Returns
    -------
    list
        a list of available datamodels
    """
    if SDSSDataModel:
        dm = SDSSDataModel()
        return dm.products.list_products()

    return generate_product_list(release=release)



def release_check(meth=None, *, attr: str = 'hdus'):
    """ Decorator to check for release model attributes

    Decorator that checks for specified attributes on a
    ``ReleaseModel``.  The default is to check the ``ReleaseModel``
    has a valid ``hdus`` attribute.

    Parameters
    ----------
    meth : _type_, optional
        the method name, by default None
    attr : str, optional
        the attribute to check against, by default 'hdus'
    """
    def decorator(method):
        @wraps(method)
        def inner(*args, **kwargs):
            ref = args[0]
            if (not hasattr(ref, 'release_model') or
                not hasattr(ref.release_model, attr) or
                not getattr(ref.release_model, attr)):
                return
            else:
                return method(*args, **kwargs)
        return inner
    return decorator(meth) if meth else decorator


@dataclass
class Model:
    """ Class that represents an SDSS datamodel

    Convenience class to interact with an SDSS datamodel object.

    Parameters
    ----------
    name : str, optional
        the file species name of the datamodel, by default ''
    release : str, optional
        the data release to extract from the datamodel, by default the global release

    """
    name : str = ''
    _model : ProdModel = field(repr=False, default=None)
    release : str = field(repr=False, default=config.release)

    summary : str = field(default='', init=False)
    description : str = field(repr=False, default='', init=False)
    datatype : str = field(repr=False, default='', init=False)
    vac : str = field(repr=False, default=False, init=False)
    recommended_science_product : str = field(repr=False, default=False, init=False)
    releases : list = field(default_factory=list, repr=False, init=False)

    def __post_init__(self):
        if not self._model:
            return

        self.name = self._model.general.name
        self.summary = self._model.general.short
        self.description = self._model.general.description
        self.datatype = self._model.general.datatype
        self.vac = self._model.general.vac
        self.recommended_science_product = self._model.general.recommended_science_product

        self.releases = [i.name for i in self._model.general.releases]

        # set the initial release
        self.set_release()

    def set_release(self, release: str = None):
        """ Set the data release of the model

        For the specified data release, sets the
        ``release_model`` to the specified ``ReleaseModel``
        from the datamodel.  This is a convenience method to
        avoid drilling down into the model.

        Parameters
        ----------
        release : str, optional
            the data release, by default None

        Raises
        ------
        ValueError
            when the data release specified is not an allowed release
        """
        release = release or self.release or config.release
        self.release = release
        if release not in self.releases:
            log.warning(f'Release {release} is not a valid release for model "{self.name}".')
            self.release_model = None
        else:
            self.release_model = copy.deepcopy(self._model.releases[release])

    @release_check
    def get_hdu(self, ext: Union[int, str]):
        """ Get an HDU model

        Retrieve an HDU model from the ``release_model``. Can either
        specify the HDU extension number or name.  Returns

        Parameters
        ----------
        ext : Union[int, str]
            the name or number of the HDU extension

        Returns
        -------
        datamodel.models.filetypes.fits.HDU
            an HDU object representation
        """

        if type(ext) == int:
            extname = f'hdu{ext}'
        elif isinstance(ext, str) and ext.isdigit():
            extname = f'hdu{ext}'
        elif isinstance(ext, str):
            extval = [v for h, v in self.release_model.hdus.items() if v.name==ext.upper()]
            if not extval:
                log.warning(f'No hdu extension found in model by name {ext.upper()}')
            return extval[0] if extval else None

        if extname not in self.release_model.hdus:
            log.warning(f'No hdu extension found in model by index {ext}.')
            return

        return self.release_model.hdus[extname]

    @release_check
    def list_hdus(self, names: bool = None) -> Union[list, dict]:
        """ List the available HDUs

        Returns a dictionary of HDU model objects from the datamodel.
        To return a list of HDU string names, set the ``names``
        keyword to True.

        Parameters
        ----------
        names : bool, optional
            If set, returns the HDU extension names, by default None

        Returns
        -------
        Union[list, dict]
            A list or dict of available HDUs
        """
        if names:
            return [i.name for i in self.release_model.hdus.values()]
        else:
            return self.release_model.hdus

    @classmethod
    def from_datamodel(cls, model: Union[str, ProdModel], release: str = None) -> ModelType:
        """ Instantiate a Model from a datamodel

        Class method to instantiate a Model object from an input datamodel object
        or a file species string name, and a data release.

        Parameters
        ----------
        model : Union[str, ProdModel]
            the object model or the file species string name
        release : str, optional
            the data release, by default None

        Returns
        -------
        ModelType
            an instance of the Model object
        """
        if isinstance(model, BaseModel):
            mod = model
        elif isinstance(model, str):
            mod = get_datamodel(model, release=release)
        return Model(_model=mod, release=release)

    @release_check(attr='access')
    def get_access_info(self, key: str = None) -> Union[dict, str, list]:
        """ Get the sdss access info from the datamodel

        Get the sdss access path information from the datamodel
        for the set ``release_model``. By default returns the
        entire dictionary of access info.  Setting the ``key``
        input retrieves a subset of info.  "name" retrieves just the
        access path name, "template" retrieves just the access path
        template, and "kwargs" retrieves just the list of required
        path keyword arguments.

        Parameters
        ----------
        key : str, optional
            the subset of access info to retrieve, by default None

        Returns
        -------
        Union[dict, str, list]
            the access information
        """

        dd = self.release_model.access.dict(exclude={'access_string'})
        if key == 'name':
            return dd['path_name']
        elif key == 'template':
            return dd['path_template']
        elif key in {'kwargs', 'keywords', 'keys'}:
            return dd['path_kwargs']
        else:
            return dd



class Models(list):
    """ Class of a list of all the datamodels

    Convenience class that represents a list of all
    available SDSS datamodels.

    Parameters
    ----------
    items : list
        A list of SDSS datamodels
    """

    def get_model(self, index: Union[int, str], release: str = None) -> ProdModel:
        """ Get a Model instance for a given datamodel

        Returns a ``Model`` instance for a given datamodel in the list
        of models.  Can provide a list index or the file species name of the
        datamodel. Can optionally provide the data release to extract.

        Parameters
        ----------
        index : Union[int, str]
            a list index or species name
        release : str, optional
            the data release, by default None

        Returns
        -------
        ProdModel
            an instance of the Model
        """
        if isinstance(index, int):
            name = self[index]
        elif isinstance(index, str):
            name = self[self.index(index)]
        return Model.from_datamodel(name, release=release)

    @classmethod
    def from_datamodels(cls, release: str = None) -> ModelsType:
        """ Instantiate a new list of models

        Class method to instantiate a new list of datamodels
        for a given data release.

        Parameters
        ----------
        release : str, optional
            the data release, by default None

        Returns
        -------
        ModelsType
            an instance of a list of models
        """
        return cls(list_datamodels(release=release))



models = Models(list_datamodels(release=config.release))


def create_object_model(name: str, release: str = None) -> ModelType:
    """ Create a datamodel object

    Create a datamodel object for a given file species
    product name and data release.

    Parameters
    ----------
    name : str
        a file species product name
    release : str, optional
        the SDSS data release, by default None

    Returns
    -------
    ModelType
        an instance of a product datamodel
    """
    if not name:
        return None

    mod = Model.from_datamodel(name, release=release)
    if mod and not mod.name:
        log.warning(f'No model found for product: {name}.')
        return

    return mod

