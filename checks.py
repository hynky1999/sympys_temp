#!/usr/bin/env python3

from checks_lib.testing_func.equiv_literal import equiv_literal
from checks_lib.testing_func.equiv_graph import equiv_graph
from checks_lib.testing_func.equiv_symbolic import equiv_symbolic
from checks_lib.testing_func.equiv_value import equiv_value
from checks_lib.testing_func.equiv_set import equiv_set
from checks_lib.testing_func.test_minor import string_match
from checks_lib.testing_func.test_minor import is_simplified
from checks_lib.testing_func.test_minor import is_expanded
from checks_lib.testing_func.test_minor import is_factorised
from checks_lib.testing_func.test_minor import is_rationalized
from checks_lib.testing_func.test_minor import is_rational
from checks_lib.testing_func.test_minor import is_true
from checks_lib.testing_func.test_minor import is_unit
from checks_lib.testing_func.test_minor import equiv_syntax
from checks_lib.testing_func.calculate import calculate
from checks_lib.js_conversion.convert_JS import convert_JS


from checks_lib.default_values import check_func
from checks_lib.parse_checks import parse_checks

check_func = {func:globals()[trans] for (func,trans) in check_func.items()}
