from django import forms


class SessionCreateForm(forms.Form):
    token = forms.CharField(required=True)
    numberToDial = forms.CharField(required=True)
    campaignid = forms.IntegerField(required=True)
    command = forms.CharField(required=True)
