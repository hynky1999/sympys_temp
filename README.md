# math-engine

## Known problems with converting latex to sympy with latex2sympy

Problems with latex2sympy conversions generally fall into one of the following categories:

### latex2sympy can't parse a legitimate LaTeX notation:

1. {Solved:preprocessing} Percent sign (\%). This is solved by catching all such instances with regex
before any conversions and manually converting them into an appropriate number.
2. {Solved:preprocessing} Notation \log_a x (one symbol after underscore) is not parsed as log. This
is solved by preprocessing LaTeX string with regex to add {}:
\log_a x -> \log_{a} x
3. {Solved:preprocessing} Instances of multiplication of a variable and/or symbolic coefficient by
an expression in parentheses, such as a(x+1) or x(x+1). Solved by preprocessing
LaTeX string with regex to add asterisk:
x(x+1) -> x\*(x+1)

### latex2sympy always performs some simplifications that should not be performed in some modes

1. 1\*(expression) is always converted to that expression without 1\*, which poses a problem with equivLiteral,
because it basically renders ignoreCoefficientOfOne on "by default".
(see test cases 10 and 22).
2. Members of a polynomial seem to be reordered canonically, e.g., 1+x and x+1 both evaluate to x+1, which
likewise poses a problem with equivLiteral without ignoreOrder option, i.e., ignoreOrder is on "by default"
due to latex2cympy conversion peculiarities and can not be simply turned off (see test case 11).
3. Not exactly latex2sympy problem but closely related to the above: any numbers with decimal separator are threated
by sympy as floats with some large precision after conversion, no matter what their precision was before, thus
enabling ignoreTrailingZeros option for equivLiteral "by default", and there is also no easy way to turn it off
(see test case 12).
4. {Solved:preprocessing} Negative fractions, such as -\frac{a}{b} are converted to have minus in numerator, such as -a/b,
which causes problems with equivLiteral, for which they should be represented as (-1)\*a/b
in order to distinguish them from \frac{-a}{b}. Solved during LaTeX preprocessing by converting such fractions
to \frac{a}{b} \* (-1), which convert as desired if a is not 1. Numerator of 1 is converted to placeholder \one,
otherwise the fraction is still converted by latex2sympy as having -1 in numerator.
