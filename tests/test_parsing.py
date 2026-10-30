"""Fixtures estritamente sintéticas; nunca usadas na publicação."""
import pytest
from transporte.parsing import parse_jsonp,legacy_rows,rows,service_minutes,ordered_service_minutes

@pytest.mark.parametrize('raw', ['{"ok":true}', '\ufeff{"ok":true}', 'cb({"ok":true});', 'retorno.JSON({"ok":true})'])
def test_json_and_jsonp(raw):
    assert parse_jsonp(raw)=={'ok':True}

@pytest.mark.parametrize('raw',['alert(1);cb({"ok":true})','cb({"x":NaN});alert(1)','cb({});evil()','/* script */ cb({})'])
def test_reject_executable_payloads(raw):
    with pytest.raises((ValueError,Exception)):parse_jsonp(raw)

@pytest.mark.parametrize('value', ["[{'cod':'1','nom':\"D'ÁGUA\"}]",["{'cod':'1','nom':\"D'ÁGUA\"}"]])
def test_legacy_quotes(value):
    assert legacy_rows(value)[0]['nom']=="D'ÁGUA"

def test_legacy_no_execution():
    with pytest.raises((ValueError,SyntaxError)):legacy_rows("__import__('os').getcwd()")

def test_contract_changes():
    with pytest.raises(ValueError):rows('[{"other":1}]',('LINHA',))

def test_midnight():
    assert ordered_service_minutes(['23:50','00:10','01:00'])==[1430,1450,1500]
    assert service_minutes('25:10')==1510

def test_disordered_schedule():
    with pytest.raises(ValueError):ordered_service_minutes(['09:00','08:00'])

@pytest.mark.parametrize('value',['1:00','00:99','48:00',None])
def test_invalid_time(value):
    with pytest.raises(ValueError):service_minutes(value)
