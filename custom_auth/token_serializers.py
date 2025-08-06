from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from custom_auth.serializers import UserSerializer
from company.serializers import CompanySerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        # Add user data via dynamic serializer
        data['user'] = UserSerializer(self.user).data
        data['company'] = CompanySerializer(self.user.company).data

        return data
