import ast
import json
import re


def parse_jsonp(raw: str):
    """Aceita só JSON ou um callback simples contendo JSON; nunca eval/exec."""
    raw = raw.lstrip('\ufeff').strip()
    if raw.startswith(('{', '[')):
        return json.loads(raw)
    match = re.fullmatch(r'[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\s*\((.*)\)\s*;?', raw, re.S)
    if not match:
        raise ValueError('JSON/JSONP inválido')
    return json.loads(match.group(1))


def legacy_rows(value):
    """SIU pode retornar lista com UMA string contendo vários dicionários."""
    if value in (None, ''):
        return []
    if isinstance(value, list) and all(isinstance(x, dict) for x in value):
        return value
    if isinstance(value, list):
        value = ','.join(value)
    if not isinstance(value, str) or len(value) > 5_000_000:
        raise ValueError('Contrato legado inválido')
    text = value.strip()
    if not text.startswith('['):
        text = '[' + text + ']'
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        result = ast.literal_eval(text)
    if not isinstance(result, list) or not all(isinstance(x, dict) for x in result):
        raise ValueError('Esperada lista de objetos')
    return result


def rows(raw, required=()):
    value = parse_jsonp(raw)
    if not isinstance(value, list) or not all(isinstance(x, dict) and all(k in x for k in required) for x in value):
        raise ValueError('Mudança de esquema: campos obrigatórios ausentes')
    return value


def service_minutes(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{2}:\d{2}', value):
        raise ValueError('Horário inválido')
    hour, minute = map(int, value.split(':'))
    if hour > 47 or minute > 59:
        raise ValueError('Horário fora do intervalo de serviço')
    return hour * 60 + minute


def ordered_service_minutes(times):
    """Preserva ordem da fonte e reconhece UMA virada de meia-noite."""
    result, offset, previous = [], 0, None
    for value in times:
        minute = service_minutes(value)
        if previous is not None and minute + offset < previous:
            if previous % 1440 >= 1080 and minute < 360 and offset == 0:
                offset = 1440
            else:
                raise ValueError('Sequência de horários fora de ordem')
        minute += offset
        result.append(minute)
        previous = minute
    return result
