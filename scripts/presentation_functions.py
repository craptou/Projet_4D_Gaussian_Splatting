"""Resolve presentation function references against real source, without importing GPU code."""
import ast
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
UPSTREAM_SHA='843d5ac636c37e4b611242287754f3d4ed150144'


@lru_cache(None)
def syntax(file):
    return ast.parse((ROOT/file).read_text(encoding='utf-8'))


def resolve(reference):
    file=reference['file'];wanted=reference['qualname'];tree=syntax(file)
    if reference.get('kind')=='call':
        matches=[node.lineno for node in ast.walk(tree) if isinstance(node,ast.Call) and ast.unparse(node.func)==wanted]
    else:
        matches=[]
        def visit(nodes,prefix=''):
            for node in nodes:
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                    name=prefix+node.name
                    if name==wanted and not isinstance(node,ast.ClassDef):matches.append(node.lineno)
                    visit(node.body,name+'.')
        visit(tree.body)
    if not matches:raise ValueError(f'Function reference not found: {file}:{wanted}')
    line=min(matches)
    if file.startswith('third_party/4DGaussians/'):
        url=f'https://github.com/hustvl/4DGaussians/blob/{UPSTREAM_SHA}/'+file.removeprefix('third_party/4DGaussians/')
    else:url='https://github.com/craptou/Projet_4D_Gaussian_Splatting/blob/main/'+file
    return dict(reference,line=line,url=url+f'#L{line}')
