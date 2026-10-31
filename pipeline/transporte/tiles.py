"""PMTiles vetorial determinístico das bases reais. Geometrias ausentes ficam ausentes."""
import gzip
import hashlib
import json
from pathlib import Path
import mercantile
import mapbox_vector_tile
from pmtiles.writer import Writer
from pmtiles.tile import Compression, TileType, zxy_to_tileid
from pyproj import Transformer
from shapely import make_valid
from shapely.geometry import shape, mapping, box
from shapely.ops import transform, unary_union
from .http import utcnow
from .collect import dump

WEB = Transformer.from_crs(4326, 3857, always_xy=True).transform
LAYERS = [('bairros','bairros-oficiais.geojson'),('setores','censo2022-setores.geojson'),
          ('limite','boundary.geojson'),('linhas','route-shapes.geojson'),('paradas','stops.geojson')]


def properties(value):
    return {k:v for k,v in value.items() if isinstance(v,(str,int,float,bool)) and v is not None}


def build_pmtiles(root, minzoom=8, maxzoom=13):
    root=Path(root);public=root/'public/data';now=utcnow()
    shapes_path=public/'route-shapes.geojson'
    if not shapes_path.exists():
        dump(shapes_path,{'type':'FeatureCollection','status':'pending','features':[],
             'description':'Sem geometrias reais validadas; nenhum percurso foi inferido de nomes de ruas.'})
    data,counts,hashes={}, {}, {}
    bounds=[]
    for layer,filename in LAYERS:
        path=public/filename;j=json.loads(path.read_text())
        hashes[filename]=hashlib.sha256(path.read_bytes()).hexdigest()
        features=[]
        for i,f in enumerate(j['features']):
            g=make_valid(shape(f['geometry']))
            if g.is_empty:continue
            if layer=='linhas' and g.geom_type not in ('LineString','MultiLineString'):
                raise ValueError('Trajeto exige geometria linear')
            features.append((i,transform(WEB,g),properties(f.get('properties') or {})))
            bounds.append(g)
        data[layer]=features;counts[layer]=len(features)
    if not data['bairros']:raise ValueError('PMTiles exige base territorial válida')
    extent=unary_union(bounds).bounds
    output=public/'transporte-canoas.pmtiles';temporary=root/'var/tmp/transporte-canoas.pmtiles.tmp'
    temporary.parent.mkdir(parents=True,exist_ok=True)
    tiles=[]
    for z in range(minzoom,maxzoom+1):
        for tile in mercantile.tiles(*extent,z):
            tiles.append((zxy_to_tileid(tile.z,tile.x,tile.y),tile))
    written=0
    with temporary.open('wb') as stream:
        writer=Writer(stream)
        for tileid,t in sorted(tiles):
            b=mercantile.xy_bounds(t);tilebox=box(b.left,b.bottom,b.right,b.top)
            # Um pixel de buffer previne costuras, sem alterar a fonte de análise.
            buffered=tilebox.buffer((b.right-b.left)/256)
            encoded_layers=[]
            for name,features in data.items():
                encoded=[]
                for fid,geom,props in features:
                    if not buffered.intersects(geom):continue
                    clipped=geom.intersection(buffered)
                    if clipped.is_empty:continue
                    if clipped.geom_type=='GeometryCollection':
                        parts=[g for g in clipped.geoms if g.geom_type==geom.geom_type]
                        if not parts:continue
                        clipped=unary_union(parts)
                    clipped=clipped.simplify((b.right-b.left)/8192,preserve_topology=True)
                    if clipped.is_empty or clipped.geom_type=='GeometryCollection':continue
                    encoded.append({'id':fid+1,'geometry':mapping(clipped),'properties':props})
                if encoded:encoded_layers.append({'name':name,'features':encoded})
            if not encoded_layers:continue
            raw=mapbox_vector_tile.encode(encoded_layers,default_options={
                'quantize_bounds':(b.left,b.bottom,b.right,b.top),'extents':4096,'y_coord_down':False})
            writer.write_tile(tileid,gzip.compress(raw,mtime=0));written+=1
        metadata={'name':'Transporte Canoas · bases locais','format':'pbf','version':'1',
            'description':'Bairros e Censo 2022; linhas apenas quando importadas de geometria real.',
            'attribution':'GeoCanoas / Prefeitura de Canoas; IBGE Censo 2022',
            'bounds':list(extent),'source_hashes':hashes,'layer_feature_counts':counts,
            'vector_layers':[{'id':name,'fields':{},'minzoom':minzoom,'maxzoom':maxzoom} for name,_ in LAYERS if counts[name]],
            'boundary_is_official':False,'method':'pmtiles-mvt-0.2.0'}
        header={'tile_compression':Compression.GZIP,'tile_type':TileType.MVT,
            'min_lon_e7':round(extent[0]*1e7),'min_lat_e7':round(extent[1]*1e7),
            'max_lon_e7':round(extent[2]*1e7),'max_lat_e7':round(extent[3]*1e7),'center_zoom':11}
        writer.finalize(header,metadata)
    temporary.replace(output)
    routes=json.loads((public/'network.json').read_text())['routes']
    geometries=json.loads(shapes_path.read_text())['features']
    present=sorted({str(f['properties']['route_id']) for f in geometries})
    index={r['id']:{'status':'available' if r['id'] in present else 'pending',
           'shape_count':sum(f['properties']['route_id']==r['id'] for f in geometries)} for r in routes}
    manifest={'schema_version':1,'generated_at':now,'file':output.name,'format':'PMTiles v3 / MVT',
        'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'bytes':output.stat().st_size,
        'bounds':list(extent),'minzoom':minzoom,'maxzoom':maxzoom,'tile_count':written,
        'layers':counts,'route_geometry_count':len(present),'route_catalogue_count':len(routes),
        'route_status':index,'source_hashes':hashes,'source_geometry_is_generalized_in_tiles':True,
        'limit':'O contorno é união dos bairros; MVT não substitui as fontes completas para análises métricas.'}
    dump(public/'map-manifest.json',manifest)
    print(json.dumps({'event':'pmtiles_built','tiles':written,'bytes':manifest['bytes'],'layers':counts}))
    return manifest


if __name__=='__main__':
    build_pmtiles(Path(__file__).resolve().parents[2])
