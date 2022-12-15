# !/usr/bin/env python
# -*- coding: utf-8 -*-
#

import pytest
import json
import pathlib
import importlib
import respx
from httpx import Response
from pydantic import BaseModel

from sdss_brain.datamodel.products import (Model, Models, generate_product_model,
                                           create_product_schema, get_datamodel, list_datamodels,
                                           generate_product_list, SDSSDataModel,
                                           get_product_model)

def test_models():
    mods = Models(['aaa', 'bbb', 'ccc'])
    assert mods[1] == 'bbb'

    mm = mods.get_model(0)
    assert isinstance(mm, Model)
    assert mm.name == ''

    am = mods.get_model('aaa')
    assert am == mm



def mock_list():
    data = {"products": ["sdR", "specLite", "test"]}
    url = 'https://api.sdss.org/valis/info/products'
    request = respx.get(url).mock(return_value=Response(200, json=data))


def get_data(schema=None):
    ff = 'schema.json' if schema else 'fitsfile.json'
    pp = pathlib.Path(__file__).parent / ff
    with open(pp, 'r') as f:
        data = json.load(f)
    return data


def mock_model(schema=None):
    data = get_data(schema=schema)

    path = f'info/{"schema" if schema else "products"}/test'
    url = f'https://api.sdss.org/valis/{path}'
    request = respx.get(url).mock(return_value=Response(200, json=data))
    return data


@pytest.fixture()
def mock_schema(monkeypatch, tmp_path):
    d = tmp_path / "products"
    d.mkdir()
    p = d / "product_schema.py"
    monkeypatch.setattr('sdss_brain.datamodel.products.product_schema_path', p)
    yield p
    p = None


@pytest.fixture()
@respx.mock
def testmodel():
    mock_model(schema=True)
    mock_model(schema=False)
    return generate_product_model("test", release="DR17")


@pytest.fixture()
def fakemodel(testmodel):
    return Model(_model=testmodel, release='DR17')


@respx.mock
def test_generate_product_list():
    mock_list()
    datamodels = generate_product_list(release='DR17')
    assert datamodels == ['sdR', 'specLite', 'test']


@pytest.mark.parametrize('local', [True, False], ids=['local', 'remote'])
@respx.mock
def test_list_datamodels(mocker, local):
    prods = ["sdR", "specLite", "test"]
    if local and SDSSDataModel:
        mocker.patch('datamodel.products.product.DataProducts.list_products', return_value=prods)
    else:
        mocker.patch('sdss_brain.datamodel.products.SDSSDataModel', new=None)
        mock_list()

    datamodels = list_datamodels(release='DR17')
    assert datamodels == prods



@pytest.mark.parametrize('schema', [True, False], ids=['schema', 'model'])
@respx.mock
def test_get_product_schema(schema):
    data = mock_model(schema=schema)

    output = get_product_model('test', release='DR17', schema=schema)
    assert output == data


def test_create_schema(mock_schema):
    schema = get_data(schema=True)
    create_product_schema(schema)
    assert mock_schema.exists()


@respx.mock
def test_generate_product_model(testmodel):
    assert testmodel.general.name == 'test'
    assert testmodel.general.short == 'this is a test file'


@pytest.mark.parametrize('local', [True, False], ids=['local', 'remote'])
@respx.mock
def test_get_datamodel(mocker, local, testmodel):

    mock_model(schema=True)
    mock_model(schema=False)

    if local and SDSSDataModel:
        pytest.skip('skipping local get datamodel for now')
        #mocker.patch('datamodel.products.product.DataProducts.__getitem__', return_value=testmodel)
    else:
        mocker.patch('sdss_brain.datamodel.products.SDSSDataModel', new=None)
        mock_model(schema=False)


    model = get_datamodel("test", release='DR17')
    assert model.general.name == 'test'
    assert model.general.short == 'this is a test file'
    assert model.general.releases[0].name == 'DR17'

    assert isinstance(model, BaseModel)

def test_model(fakemodel):
    assert fakemodel.name == 'test'
    assert fakemodel.summary == 'this is a test file'
    assert fakemodel.release == 'DR17'


def test_model_fromdm(fakemodel, testmodel):
    model = Model.from_datamodel(testmodel, release='DR17')
    assert model == fakemodel


def test_model_list_hdus(fakemodel):
    hdus = fakemodel.list_hdus()
    assert len(hdus) == 3
    assert hdus['hdu0'].name == 'PRIMARY'
    assert hdus['hdu2'].name == 'PARAMS'

@pytest.mark.parametrize('ext, exp',
                         [(0, "PRIMARY"),
                          ('0', "PRIMARY"),
                          ("PARAMS", "PARAMS")],
                          ids=['primary', 'strprim', 'params'])
def test_model_get_hdus(fakemodel, ext, exp):
    assert fakemodel.get_hdu(ext).name == exp


access_data = {"in_sdss_access": True, "path_name": "test",
               "path_template": "$TEST_REDUX/{ver}/testfile_{id}.fits",
               "path_kwargs": ["ver", "id" ]}

@pytest.mark.parametrize('key, exp',
                         [('name', "test"),
                          ("template", "$TEST_REDUX/{ver}/testfile_{id}.fits"),
                          ("kwargs", ["ver", "id"]),
                          (None, access_data),
                          ('other', access_data)],
                          ids=['name', 'template', 'kwargs', 'none', 'else'])
def test_model_get_access(fakemodel, key, exp):
    assert fakemodel.get_access_info(key) == exp
