# math_eval.py
import ast
import math
from decimal import Decimal, ROUND_DOWN, InvalidOperation


class MathEvalError(Exception):
    """数式評価に失敗したときの独自例外"""
    pass

# ==============================
#  小数第3位で「切り捨て」関数
#  4.2325 -> 4.232
# ==============================
def truncate_3(x: float) -> float:
    """
    小数第3位でカットする（丸めではなく切り捨て）。
    例: 4.2325 -> 4.232
    """
    try:
        d = Decimal(str(x))
        # 0.001 単位で ROUND_DOWN（絶対値方向ではなく常に小さくする）
        d = d.quantize(Decimal("0.001"), rounding=ROUND_DOWN)
        return float(d)
    except (InvalidOperation, ValueError):
        # 何かおかしければそのまま返す
        return x


# ==============================
#  安全な数式 evaluator 本体
# ==============================
class SafeEvaluator(ast.NodeVisitor):
    """
    四則演算 / 括弧 / 累乗 / sqrt だけを許可する安全な evaluator。
    - 使える演算子: + - * / ** (^ は ** に変換)
    - 使える関数: sqrt(...)
    """

    ALLOWED_BINOPS = (
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
    )

    ALLOWED_UNARYOPS = (
        ast.UAdd,
        ast.USub,
    )

    ALLOWED_FUNCS = {
        "sqrt": math.sqrt,
    }

    def visit(self, node):
        # 許可されていないノードは全部弾く
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        raise MathEvalError(f"この種類の式は許可されていません: {node.__class__.__name__}")

    def visit_Expression(self, node: ast.Expression):
        return self.visit(node.body)

    def visit_BinOp(self, node: ast.BinOp):
        if not isinstance(node.op, self.ALLOWED_BINOPS):
            raise MathEvalError("許可されていない演算子です")

        left = self.visit(node.left)
        right = self.visit(node.right)

        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left ** right

        raise MathEvalError("未対応の演算子です")

    def visit_UnaryOp(self, node: ast.UnaryOp):
        if not isinstance(node.op, self.ALLOWED_UNARYOPS):
            raise MathEvalError("未対応の単項演算子です")

        operand = self.visit(node.operand)
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, ast.USub):
            return -operand

        raise MathEvalError("未対応の単項演算子です")

    def visit_Call(self, node: ast.Call):
        # 関数呼び出しは sqrt(...) のみ許可
        if not isinstance(node.func, ast.Name):
            raise MathEvalError("未対応の関数呼び出しです")

        func_name = node.func.id
        if func_name not in self.ALLOWED_FUNCS:
            raise MathEvalError(f"使用できない関数です: {func_name}")

        func = self.ALLOWED_FUNCS[func_name]

        if len(node.args) != 1:
            raise MathEvalError("関数は1引数のみ対応です")

        arg_val = self.visit(node.args[0])
        return func(arg_val)

    def visit_Name(self, node: ast.Name):
        # 変数は禁止
        raise MathEvalError("変数は利用できません")

    def visit_Constant(self, node: ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise MathEvalError("数値以外のリテラルは利用できません")

    # Python 3.7 系などで Num が来る場合に備えて
    def visit_Num(self, node: ast.Num):  # type: ignore[override]
        return float(node.n)


def eval_expr(expr: str) -> float:
    """
    数式文字列を安全に評価して float を返す。
    - 使用例:
        eval_expr("1+2*3")          -> 7.0
        eval_expr("sqrt(3*3+4*4)")  -> 5.0
        eval_expr("2^3")            -> 8.0  （内部で 2**3 に変換）
    - 失敗した場合は MathEvalError を投げる。
    """
    if expr is None:
        raise MathEvalError("空の式です")

    # 前後の空白を除去
    src = expr.strip()

    if not src:
        raise MathEvalError("空の式です")

    # ^ を ** に変換（累乗用）
    src = src.replace("^", "**")

    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError as e:
        raise MathEvalError("式の構文が正しくありません") from e

    evaluator = SafeEvaluator()
    value = evaluator.visit(tree)
    return float(value)


def eval_and_truncate_3(expr: str) -> float:
    """
    式を評価し、小数第3位で切り捨てた値を返すユーティリティ。
    例:
        "4.2325" -> 4.232
        "154.2+8" -> 162.2
    """
    val = eval_expr(expr)
    return truncate_3(val)
