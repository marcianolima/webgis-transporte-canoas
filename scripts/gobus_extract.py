"""Converte respostas SIU/GoBus salvas localmente. Não realiza requisições."""
import argparse
import json
from pathlib import Path
from transporte import gobus

def main():
    p = argparse.ArgumentParser(description='Leitura offline de uma resposta JSONP SIU')
    p.add_argument('recurso', choices=('linhas', 'paradas', 'itinerario', 'veiculos', 'previsoes'))
    p.add_argument('arquivo', type=Path, help='Resposta recebida legitimamente e salva em arquivo')
    p.add_argument('--itinerario-id', help='ID exato do itinerário; obrigatório para recurso itinerario')
    args = p.parse_args()
    if args.arquivo.stat().st_size > 15_000_000:
        p.error('Resposta acima de 15 MB')
    raw = args.arquivo.read_text(encoding='utf-8-sig')
    if args.recurso == 'itinerario':
        if not args.itinerario_id or not args.itinerario_id.isdecimal():
            p.error('--itinerario-id numérico é obrigatório')
        result = gobus.itinerary(raw, args.itinerario_id)
    else:
        parsers = {'linhas': gobus.lines, 'paradas': gobus.stops,
                   'veiculos': gobus.vehicles, 'previsoes': gobus.predictions}
        result = parsers[args.recurso](raw)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
