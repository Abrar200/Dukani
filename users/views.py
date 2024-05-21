from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from users.models import CustomUser
from django.contrib import messages

def user_register_view(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmPassword')
        print(f"{password} and {confirm_password}")

        if password == confirm_password:
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists.')
            else:
                user = CustomUser.objects.create_user(username=username, first_name=first_name, last_name=last_name, email=email, password=password)
                messages.success(request, 'Registration successful. You can now log in.')
                return redirect('login')
        else:
            messages.error(request, 'Passwords do not match.')

    return render(request, 'users/user_registration.html')

def user_login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        CustomUser = authenticate(request, username=username, password=password)

        if CustomUser is not None:
            login(request, CustomUser)
            messages.success(request, 'Login successful.')
            return redirect('home')  # Replace 'home' with the URL name of your desired destination
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'users/user_login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'Logout successful.')
    return redirect('login')

def profile(request, username):
    username = request.user.username
    return render(request, "users/profile.html")