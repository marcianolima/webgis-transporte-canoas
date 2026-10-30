"""Triagem offline do APK obtido legitimamente. Não decompila nem executa código."""
import argparse,hashlib,json,re,zipfile
from pathlib import Path
from urllib.parse import urlsplit
parser=argparse.ArgumentParser();parser.add_argument('apk',type=Path);args=parser.parse_args()
if args.apk.stat().st_size>250_000_000:raise SystemExit('Arquivo acima do limite de 250 MB')
result={'apk_sha256':hashlib.sha256(args.apk.read_bytes()).hexdigest(),'analysis':'static-strings-only','files':[]}
with zipfile.ZipFile(args.apk) as archive:
    if sum(i.file_size for i in archive.infolist())>500_000_000:raise SystemExit('Conteúdo descompactado acima de 500 MB')
    for info in archive.infolist():
        if info.file_size>30_000_000 or not info.filename.endswith(('.js','.html','.json','.xml','.dex','.properties')):continue
        data=archive.read(info).decode('utf-8',errors='ignore');hosts=set()
        for text in re.findall(r'https?://[^\s"\x27<>\\]{5,250}',data):
            try:
                value=urlsplit(text)
                if value.hostname:hosts.add(value.scheme+'://'+value.hostname+((':'+str(value.port)) if value.port else ''))
            except ValueError:pass
        resources=sorted(set(re.findall(r'(?:V3/)?(?:buscarLinhas|buscarParadas\w*|retornaVeiculos\w*|retornaQroLinha|buscarItinerario|buscarPrevisoes)',data)))
        if hosts or resources:result['files'].append({'path':info.filename,'hosts_only':sorted(hosts),'resources':resources})
print(json.dumps(result,ensure_ascii=False,indent=2))
