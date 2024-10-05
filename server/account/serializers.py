from rest_framework import serializers
from account.models import User, Consumer
from django.utils.encoding import smart_str,force_bytes,DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode,urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from account.utils import Util
import re

class UserRegistrationSerializer(serializers.ModelSerializer):
    password2=serializers.CharField(style={'input_type':'password'},write_only=True)
    class Meta:
        model=User
        fields=['name','email','password','password2','tc']
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 5},
        }

    def validate(self, attrs):
        password=attrs.get('password')
        password2=attrs.get('password2')
        if password!=password2:
            raise serializers.ValidationError({'Password and Confirm Password does not match'})
        return attrs
    
    def create(self, validate_data):
        return User.objects.create_user(**validate_data)
    
class UserLoginSerializer(serializers.ModelSerializer):
    email=serializers.EmailField(max_length=255)
    class Meta:
        model=User
        fields=['email','password']

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model=User
        fields=['id','name','email']

class ConsumerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consumer
        fields = ['user', 'shipping_address', 'phone_number', 'age', 'gender', 'created_at', 'updated_at']
        
    def validate_phone_number(self, value):
        phone_regex = re.compile(r'^\+\d{1,2} \d{10}$')  # Ensures + followed by 1-2 digits and 10 digits after a space
        if not phone_regex.match(value):
            raise serializers.ValidationError("Phone number must be in the format '+XX XXXXXXXXXX', where XX is the country code and XXXXXXXXXX is the 10-digit number.")
        return value


class UserChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        max_length=255, style={'input_type': 'password'}, write_only=True
    )
    password2 = serializers.CharField(
        max_length=255, style={'input_type': 'password'}, write_only=True
    )

    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2')
        user = self.context.get('user')  

        if password != password2:
            raise serializers.ValidationError(
                {'password': 'Password and Confirm Password do not match'}
            )

        user.set_password(password)
        user.save()

        return attrs
    
class SendPasswordResetEmailSerializer(serializers.Serializer):
    email=serializers.EmailField(max_length=255)
    class Meta:
        fields=['email']
    
    def validate(self, attrs):
        email=attrs.get('email')
        if User.objects.filter(email=email).exists():
            user=User.objects.get(email=email)
            uid=urlsafe_base64_encode(force_bytes(user.id))
            print('encoded uid:',uid)
            token=PasswordResetTokenGenerator().make_token(user)
            print('Password Reset Token',token)
            link='http://localhost:3000/api/user/reset/'+uid+'/'+token
            print('pass reset link:',link)
            #email send
            data={
                'subject':'Reset Your Password',
                'body':f'Please use this link to reset your password {link}',
                'to_email':user.email
            }
            Util.send_email(data)
            return attrs
        else:
            raise serializers.ValidationError({'You are not registered user'})
    
class UserPasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(
        max_length=255, style={'input_type': 'password'}, write_only=True
    )
    password2 = serializers.CharField(
        max_length=255, style={'input_type': 'password'}, write_only=True
    )

    def validate(self, attrs):
        try:
            password = attrs.get('password')
            password2 = attrs.get('password2')
            uid = self.context.get('uid')  
            token = self.context.get('token')  

            if password != password2:
                raise serializers.ValidationError(
                    {'password': 'Password and Confirm Password do not match'}
                )

            id=smart_str(urlsafe_base64_decode(uid))
            user=User.objects.get(id=id)
            if not PasswordResetTokenGenerator().check_token(user,token):
                raise serializers.ValidationError({'token is invalid'})
            
            user.set_password(password)
            user.save()
            return attrs
        except DjangoUnicodeDecodeError as identifier:
            PasswordResetTokenGenerator().check_token(user,token)
            raise serializers.ValidationError({'token is invalid'})