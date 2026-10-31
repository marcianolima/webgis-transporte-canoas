"""Crosswalk TACOM e NGS: apenas candidatos, jamais autoaprovação."""
import json
import pytest
from transporte.gobus_crosswalk import propose

def jp(name, data):
    return name+'('+json.dumps(data,ensure_ascii=False)+');'

CITIES=jp('retornoJSONCidadesLinhas',{'sucesso':True,
    'cidade':["{'cod':'4','desc':'CANOAS'},{'cod':'9','desc':'ESTEIO'}"]})
LINES=jp('retornoJSONListaLinhas',{'sucesso':True,
    'linhas':"[{'cod':'17','sgl':'05006','nom':'BAIRRO/CENTRO','praca':'MPA','codcid':4},"
            "{'cod':'18','sgl':'08000','nom':'SEM CODIGO NGS','praca':'MPA','codcid':4},"
            "{'cod':'21','sgl':'05006','nom':'OUTRO MUNICIPIO','praca':'MPA','codcid':9}]"})
NETWORK={'routes':[{'id':'05006','code':'5006','name':'Bairro / Centro'}]}

def test_crosswalk_separates_canoas_and_requires_review():
    result=propose(CITIES,LINES,NETWORK)
    assert result['source_line_count']==2
    assert result['candidate_count']==1
    assert result['unmatched_count']==1
    assert result['rows'][0]['ngs_route_id']=='05006'
    assert result['rows'][0]['crosswalk_approved']=='false'
    assert result['rows'][0]['direction_review']=='pending'
    assert result['rows'][1]['match_status']=='not_matched'

def test_crosswalk_rejects_unverified_city():
    wrong=jp('retornoJSONCidadesLinhas',{'sucesso':True,
        'cidade':["{'cod':'5','desc':'CANOAS'}"]})
    with pytest.raises(ValueError):
        propose(wrong,LINES,NETWORK)

def test_crosswalk_rejects_duplicate_siu_id():
    rows=jp('retornoJSONListaLinhas',{'sucesso':True,
        'linhas':"[{'cod':'17','sgl':'05006','nom':'L1','praca':'MPA','codcid':4},"
                "{'cod':'17','sgl':'05007','nom':'L2','praca':'MPA','codcid':4}]"})
    with pytest.raises(ValueError,match='duplicado'):
        propose(CITIES,rows,NETWORK)
