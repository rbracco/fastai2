#AUTOGENERATED! DO NOT EDIT! File to edit: dev/02_data_transforms.ipynb (unless otherwise specified).

__all__ = ['type_hints', 'anno_ret', 'cmp_instance', 'ShowTitle', 'Int', 'Float', 'Str', 'subplots', 'TensorImageBase',
           'TensorImage', 'TensorImageBW', 'TensorMask', 'TypeDispatch', 'Transform', 'TupleTransform', 'ItemTransform']

from ..imports import *
from ..test import *
from ..core import *
from ..notebook.showdoc import show_doc

def type_hints(f):
    "Same as `typing.get_type_hints` but returns `{}` if not allowed type"
    return typing.get_type_hints(f) if isinstance(f, typing._allowed_types) else {}

def anno_ret(func):
    "Get the return annotation of `func`"
    if not func: return None
    ann = type_hints(func)
    if not ann: return None
    typ = ann.get('return')
    return list(typ.__args__) if getattr(typ, '_name', '')=='Tuple' else typ

cmp_instance = functools.cmp_to_key(lambda a,b: 0 if a==b else 1 if issubclass(a,b) else -1)

def _p1_anno(f):
    "Get the annotation of first param of `f`"
    hints = type_hints(f)
    ann = [o for n,o in hints.items() if n!='return']
    return ann[0] if ann else object

class ShowTitle:
    "Base class that adds a simple `show`"
    _show_args = {'label': 'text'}
    def show(self, ctx=None, **kwargs): return show_title(str(self), ctx=ctx, **merge(self._show_args, kwargs))

class Int(int, ShowTitle): pass
class Float(float, ShowTitle): pass
class Str(str, ShowTitle): pass
add_docs(Int, "An `int` with `show`"); add_docs(Str, "An `str` with `show`"); add_docs(Float, "An `float` with `show`")

@delegates(plt.subplots, keep=True)
def subplots(nrows=1, ncols=1, **kwargs):
    fig,ax = plt.subplots(nrows,ncols,**kwargs)
    if nrows*ncols==1: ax = array([ax])
    return fig,ax

class TensorImageBase(TensorBase):
    _show_args = {'cmap':'viridis'}
    def show(self, ctx=None, **kwargs):
        return show_image(self, ctx=ctx, **{**self._show_args, **kwargs})

    def get_ctxs(self, max_samples=10, rows=None, cols=None, figsize=None, **kwargs):
        n_samples = min(self.shape[0], max_samples)
        rows = rows or int(np.ceil(math.sqrt(n_samples)))
        cols = cols or int(np.ceil(math.sqrt(n_samples)))
        figsize = (cols*3, rows*3) if figsize is None else figsize
        _,axs = subplots(rows, cols, figsize=figsize)
        return axs.flatten()

class TensorImage(TensorImageBase): pass

class TensorImageBW(TensorImage): _show_args = {'cmap':'Greys'}

class TensorMask(TensorImageBase): _show_args = {'alpha':0.5, 'cmap':'tab20'}

class TypeDispatch:
    "Dictionary-like object; `__getitem__` matches keys of types using `issubclass`"
    def __init__(self, *funcs):
        self.funcs,self.cache = {},{}
        for f in funcs: self.add(f)
        self.inst = None

    def _reset(self):
        self.funcs = {k:self.funcs[k] for k in sorted(self.funcs, key=cmp_instance, reverse=True)}
        self.cache = {**self.funcs}

    def add(self, f):
        "Add type `t` and function `f`"
        self.funcs[_p1_anno(f) or object] = f
        self._reset()

    def returns(self, x): return anno_ret(self[type(x)])

    def __repr__(self): return str({getattr(k,'__name__',str(k)):v.__name__ for k,v in self.funcs.items()})

    def __call__(self, x, *args, **kwargs):
        f = self[type(x)]
        if not f: return x
        if self.inst: f = types.MethodType(f, self.inst)
        return f(x, *args, **kwargs)

    def __get__(self, inst, owner):
        self.inst = inst
        return self

    def __getitem__(self, k):
        "Find first matching type that is a super-class of `k`"
        if k in self.cache: return self.cache[k]
        types = [f for f in self.funcs if issubclass(k,f)]
        res = self.funcs[types[0]] if types else None
        self.cache[k] = res
        return res

class _TfmDict(dict):
    def __setitem__(self,k,v):
        if k=='_': k='encodes'
        if k not in ('encodes','decodes') or not isinstance(v,Callable): return super().__setitem__(k,v)
        if k not in self: super().__setitem__(k,TypeDispatch())
        res = self[k]
        res.add(v)

class _TfmMeta(type):
    def __new__(cls, name, bases, dict):
        res = super().__new__(cls, name, bases, dict)
        res.__signature__ = inspect.signature(res.__init__)
        return res

    def __call__(cls, *args, **kwargs):
        f = args[0] if args else None
        n = getattr(f,'__name__',None)
        if not hasattr(cls,'encodes'): cls.encodes=TypeDispatch()
        if not hasattr(cls,'decodes'): cls.decodes=TypeDispatch()
        if isinstance(f,Callable) and n in ('decodes','encodes','_'):
            getattr(cls,'encodes' if n=='_' else n).add(f)
            return f
        return super().__call__(*args, **kwargs)

    @classmethod
    def __prepare__(cls, name, bases): return _TfmDict()

class Transform(metaclass=_TfmMeta):
    "Delegates (`__call__`,`decode`) to (`encodes`,`decodes`) if `filt` matches"
    filt,init_enc,as_item_force,as_item,order = None,False,None,True,0
    def __init__(self, enc=None, dec=None, filt=None, as_item=True):
        self.filt,self.as_item = ifnone(filt, self.filt),as_item
        self.init_enc = enc or dec
        if not self.init_enc: return

        # Passing enc/dec, so need to remove (base) class level enc/dec
        del(self.__class__.encodes,self.__class__.decodes)
        self.encodes,self.decodes = (TypeDispatch(),TypeDispatch())
        if enc:
            self.encodes.add(enc)
            self.order = getattr(self.encodes,'order',self.order)
        if dec: self.decodes.add(dec)

    @property
    def use_as_item(self): return ifnone(self.as_item_force, self.as_item)
    def __call__(self, x, **kwargs): return self._call('encodes', x, **kwargs)
    def decode  (self, x, **kwargs): return self._call('decodes', x, **kwargs)
    def __repr__(self): return f'{self.__class__.__name__}: {self.use_as_item} {self.encodes} {self.decodes}'

    def _call(self, fn, x, filt=None, **kwargs):
        if filt!=self.filt and self.filt is not None: return x
        f = getattr(self, fn)
        if self.use_as_item: return self._do_call(f, x, **kwargs)
        return tuple(self._do_call(f, x_, **kwargs) for x_ in x)

    def _do_call(self, f, x, **kwargs):
        return x if f is None else retain_type(f(x, **kwargs), x, f.returns(x))

add_docs(Transform, decode="Delegate to `decodes` to undo transform")

class TupleTransform(Transform):
    "`Transform` that always treats `as_item` as `False`"
    as_item_force=False

class ItemTransform (Transform):
    "`Transform` that always treats `as_item` as `True`"
    as_item_force=True