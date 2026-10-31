from django import forms

from .models import Order, SavedAddress


class CheckoutForm(forms.ModelForm):
    saved_address = forms.ModelChoiceField(
        queryset=SavedAddress.objects.none(),
        required=False,
        label="Use a saved address",
    )
    address_label = forms.CharField(
        max_length=40,
        required=False,
        initial="Home",
        label="Address label",
    )
    save_address = forms.BooleanField(
        required=False,
        initial=True,
        label="Save this address or its changes for future orders",
    )

    class Meta:
        model = Order
        fields = [
            "saved_address",
            "full_name",
            "phone",
            "address_line",
            "city",
            "state",
            "pincode",
            "address_label",
            "save_address",
        ]
        labels = {"address_line": "Address", "pincode": "PIN code"}

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        addresses = SavedAddress.objects.filter(user=user)
        self.fields["saved_address"].queryset = addresses
        selected_address = None

        if self.is_bound:
            address_id = self.data.get(self.add_prefix("saved_address"))
            if address_id:
                selected_address = addresses.filter(pk=address_id).first()
                if selected_address:
                    data = self.data.copy()
                    for field_name in (
                        "full_name",
                        "phone",
                        "address_line",
                        "city",
                        "state",
                        "pincode",
                    ):
                        key = self.add_prefix(field_name)
                        if not data.get(key):
                            data[key] = getattr(selected_address, field_name)
                    self.data = data
        else:
            selected_address = addresses.first()
            if selected_address:
                self.initial.setdefault("saved_address", selected_address.pk)
                self.initial["address_label"] = selected_address.label
                for field_name in (
                    "full_name",
                    "phone",
                    "address_line",
                    "city",
                    "state",
                    "pincode",
                ):
                    self.initial[field_name] = getattr(selected_address, field_name)

    def clean_saved_address(self):
        address = self.cleaned_data.get("saved_address")
        if address and address.user_id != self.user.pk:
            raise forms.ValidationError("Choose one of your saved addresses.")
        return address


class SavedAddressForm(forms.ModelForm):
    class Meta:
        model = SavedAddress
        fields = ["label", "full_name", "phone", "address_line", "city", "state", "pincode"]
        labels = {"address_line": "Address", "pincode": "PIN code"}
