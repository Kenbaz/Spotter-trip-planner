# test_api/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404

from .models import Trip, Route, Stops, HOSPeriod, ComplianceReport