"""
WTForms
=======

WTForms is a flexible forms validation and rendering library for python web
development.

:copyright: Copyright (c) 2010 by Thomas Johansson, James Crasta and others.
:license: BSD, see LICENSE.txt for details.
"""
import os
import sys
sys.path.append(os.path.abspath(
  os.path.join(os.path.dirname(__file__), '..')
))

from wtforms import validators, widgets
from wtforms.fields import *
from wtforms.form import Form
from wtforms.validators import ValidationError

__version__ = '1.0.3dev'
