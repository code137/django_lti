from django.shortcuts import render

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django import forms
from random import randint

from inspect import getmembers
from pprint import pprint

# django lti decorator
from lti.dependencies.pylti.django import lti as lti


@csrf_exempt
@lti(role='any', req_type='initial')
def index(request, *args, **kwargs):
    return render(request, 'lti/index.html', {'lti': kwargs['lti']})


@csrf_exempt
@lti(role='any', req_type='session')
def add(request, *args, **kwargs):
    form = AddForm()
    form.fields["p1"].initial = randint(1, 9)
    form.fields["p2"].initial = randint(1, 9)

    return render(request, 'lti/add.html', {'form': form})


@csrf_exempt
@lti(role='any', req_type='session')
def grade(request, *args, **kwargs):
    """ post grade

    :param lti: the `lti` object from `pylti`
    :return: grade rendered by grade.html template
    """
    # default to false until we check the value
    correct = False

    if request.method == 'POST':
        form = AddForm(request.POST)

        if form.is_valid():
            data = form.cleaned_data
            correct = ((data['p1'] + data['p2']) == data['result'])
            kwargs['lti'].post_grade(1 if correct else 0)

    return render(request, 'lti/grade.html', {'correct': correct})


@csrf_exempt
@lti(role='instructor', req_type='session')
def instructor(request, *args, **kwargs):
    return render(request, 'lti/instructor.html', {'lti': kwargs['lti']})


@csrf_exempt
@lti(role='staff', req_type='session')
def staff(request, *args, **kwargs):
    return render(request, 'lti/staff.html', {'lti': kwargs['lti']})


def is_up(request):
    return HttpResponse("I'm up")


class AddForm(forms.Form):
    """ Add data from Form

    :param Form:
    """
    p1 = forms.IntegerField(label='p1')
    p2 = forms.IntegerField(label='p2')
    result = forms.IntegerField(label='result')
