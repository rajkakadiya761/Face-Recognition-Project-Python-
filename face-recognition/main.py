import auth

def main_menu():
    """Display main menu"""
    while True:
        print("\n" + "="*50)
        print("FACE RECOGNITION LOGIN SYSTEM")
        print("="*50)
        print("1. Register New Account")
        print("2. Login to Account")
        print("3. Exit")
        print("="*50)
        
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == '1':
            auth.register_user()
        elif choice == '2':
            username = auth.login_user()
            if username:
                logged_in_menu(username)
        elif choice == '3':
            print("\nThank you for using Face Recognition System!")
            print("Goodbye!")
            break
        else:
            print("Invalid choice! Please try again.")

def logged_in_menu(username):
    """Menu for logged-in users"""
    while True:
        print("\n" + "="*50)
        print(f"MENU - Logged in as: {username}")
        print("="*50)
        print("1. Change Password")
        print("2. Register/Update Face")
        print("3. Logout")
        print("="*50)
        
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == '1':
            auth.change_password(username)
        elif choice == '2':
            auth.add_face_to_account(username)
        elif choice == '3':
            print(f"\nLogout successful! Goodbye {username}!")
            break
        else:
            print("Invalid choice! Please try again.")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nApplication terminated by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please restart the application.")
