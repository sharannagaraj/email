from flask import Flask, render_template, request, jsonify
import re
import smtplib
import socket
import dns.resolver
import idna
from email.utils import parseaddr

app = Flask(__name__)
app.config["SECRET_KEY"] = "replace_this_with_a_secure_random_string"

def is_valid_domain(domain):
    """Check if the domain format is valid."""
    try:
        # Check basic domain format
        if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
            return False
        
        # Check if domain exists
        dns.resolver.resolve(domain, 'MX')
        return True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
        return False
    except Exception:
        return False

def is_accept_all_domain(domain):
    """Check if the domain accepts all emails."""
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_host = str(mx_records[0].exchange)
        
        # Connect to the mail server
        with smtplib.SMTP(timeout=10) as smtp:
            smtp.connect(mx_host)
            smtp.helo('test.com')
            
            # Try with a random email
            random_email = f"nonexistent_{''.join(random.choices(string.ascii_lowercase, k=10))}@{domain}"
            smtp.mail('')
            code, _ = smtp.rcpt(random_email)
            
            return code == 250
    except Exception:
        return False

def is_valid_email(email):
    """Check if the email address is valid."""
    try:
        # Basic email format validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False
        
        # Split email into local part and domain
        local_part, domain = email.split('@')
        
        # Check domain
        if not is_valid_domain(domain):
            return False
            
        return True
    except Exception:
        return False

def email_permutator(first_name, last_name, domain):
    """Generate email permutations based on first name and last name."""
    first_name = first_name.lower()
    last_name = last_name.lower()
    
    # Remove special characters and spaces
    first_name = re.sub(r'[^a-z0-9]', '', first_name)
    last_name = re.sub(r'[^a-z0-9]', '', last_name)
    
    permutations = [
        f"{first_name}@{domain}",
        f"{first_name}.{last_name}@{domain}",
        f"{first_name}{last_name}@{domain}",
        f"{first_name[0]}{last_name}@{domain}",
        f"{first_name}_{last_name}@{domain}",
        f"{first_name}-{last_name}@{domain}",
        f"{first_name[0]}.{last_name}@{domain}",
        f"{last_name}.{first_name}@{domain}",
        f"{last_name}{first_name}@{domain}",
        f"{last_name}_{first_name}@{domain}"
    ]
    
    return list(dict.fromkeys(permutations))  # Remove duplicates while maintaining order

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    error = None
    full_name = ""
    domain = ""
    
    if request.method == "POST":
        if 'reset' in request.form:
            return render_template("index.html")
            
        full_name = request.form.get("full_name", "").strip()
        domain = request.form.get("domain", "").strip()
        
        if not full_name or not domain:
            error = "Please provide both full name and domain."
            return render_template("index.html", error=error, full_name=full_name, domain=domain)
        
        names = full_name.split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""
        
        if not is_valid_domain(domain):
            error = "Invalid domain format."
            return render_template("index.html", error=error, full_name=full_name, domain=domain)
        
        email_permutations = email_permutator(first_name, last_name, domain)
        
        accept_all_counter = 0
        for email in email_permutations:
            if is_valid_email(email):
                if is_accept_all_domain(email.split('@')[1]):
                    results.append({"email": email, "status": "valid but accept-all", "class": "warning"})
                    accept_all_counter += 1
                    if accept_all_counter >= 2:
                        results.append({"email": "Stopping further checking as domain is accept-all.", "status": "info", "class": "info"})
                        break
                else:
                    results.append({"email": email, "status": "valid", "class": "success"})
                    break
            else:
                results.append({"email": email, "status": "invalid", "class": "error"})
    
    return render_template("index.html", results=results, error=error, full_name=full_name, domain=domain)

if __name__ == "__main__":
    app.run(debug=True)