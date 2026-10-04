"""说明图专用的分支探测器：按实际判断结果划分输入等价类。"""

import operator


class _SplitProbe(Exception):
    def __init__(self, axis: str, groups: list[tuple]):
        self.axis = axis
        self.groups = groups


class ProbeValue:
    """只在独立探测对象中使用，不修改注册类或生产伤害方法。

    同一范围内比较/运算结果一致时直接返回真实值；不一致时拆分范围，
    重跑独立对象。未参与判断的维度保持完整范围，不枚举其笛卡尔积。
    """

    def __init__(self, domains: dict, axis: str, project=lambda value: value):
        self.domains = domains
        self.axis = axis
        self.project = project

    def evaluate(self, operation):
        groups = {}
        for value in self.domains[self.axis]:
            result = operation(self.project(value))
            groups.setdefault((type(result), result), []).append(value)
        if len(groups) != 1:
            raise _SplitProbe(self.axis, [tuple(values) for values in groups.values()])
        return next(iter(groups))[1]

    def resolve(self):
        return self.evaluate(lambda value: value)

    def binary(self, other, operation, reverse=False):
        if isinstance(other, ProbeValue):
            other = other.resolve()
        if reverse:
            return self.evaluate(lambda value: operation(other, value))
        return self.evaluate(lambda value: operation(value, other))

    def __bool__(self):
        return self.evaluate(bool)

    def __int__(self):
        return self.evaluate(int)

    def __index__(self):
        return self.evaluate(operator.index)

    def __float__(self):
        return self.evaluate(float)

    def __str__(self):
        return self.evaluate(str)

    def __repr__(self):
        return self.evaluate(repr)

    def __format__(self, spec):
        return self.evaluate(lambda value: format(value, spec))

    def __neg__(self):
        return self.evaluate(operator.neg)

    def __pos__(self):
        return self.evaluate(operator.pos)

    def __abs__(self):
        return self.evaluate(abs)

    def __invert__(self):
        return self.evaluate(operator.invert)

    def __round__(self, digits=None):
        return self.evaluate(lambda value: round(value, digits))

    def __hash__(self):
        return self.evaluate(hash)

    def __len__(self):
        return self.evaluate(len)

    def __iter__(self):
        return iter(self.resolve())

    def __getitem__(self, key):
        return self.evaluate(lambda value: value[key])

    def __getattr__(self, name):
        # 原生标量方法也必须先解析输入，不能透传一个未划分的代表值。
        return getattr(self.resolve(), name)


def _binary_method(operation, reverse=False):
    def method(self, other):
        return self.binary(other, operation, reverse)

    return method


# 所有对象共用同一套 Python 标量协议，不登记角色、装备或增益文案。
for _name in ("eq", "ne", "lt", "le", "gt", "ge"):
    setattr(ProbeValue, f"__{_name}__", _binary_method(getattr(operator, _name)))
for _name in ("add", "sub", "mul", "truediv", "floordiv", "mod", "pow", "and", "or", "xor", "lshift", "rshift"):
    _operation = getattr(operator, _name + "_" if _name in ("and", "or") else _name)
    setattr(ProbeValue, f"__{_name}__", _binary_method(_operation))
    setattr(ProbeValue, f"__r{_name}__", _binary_method(_operation, reverse=True))


def partition_probes(domains: dict, execute):
    """产出“整个范围具有相同执行结果”的叶节点，不抽样猜测独立性。

    每次拆分覆盖原范围全部值；重跑会继续发现短路分支中后续的条件。
    因而 AND、OR、嵌套分支和上游状态写入都走实际生产调用顺序。
    """
    pending = [domains]
    while pending:
        region = pending.pop()
        try:
            result = execute(region)
        except _SplitProbe as split:
            pending.extend({**region, split.axis: values} for values in reversed(split.groups))
        else:
            yield region, result
