import time
import sys
from decimal import Decimal, getcontext

def calculate_pi(digits):
    print(f"[STATUS] Initializing math context for {digits} digits...")
    # Set precision with a safety margin of 10 digits to prevent rounding errors
    getcontext().prec = digits + 10
    
    # We use Machin's Formula: pi/4 = 4 * arctan(1/5) - arctan(1/239)
    # Using the Taylor series expansion for arccot(n):
    # arccot(n) = 1/n - 1/(3*n^3) + 1/(5*n^5) - 1/(7*n^7)...
    
    def arccot(n):
        n_sq = Decimal(n * n)
        term = Decimal(1) / Decimal(n)
        result = term
        i = 3
        sign = -1
        
        while True:
            # term = 1 / (n^(i))
            term = term / n_sq
            delta = term / Decimal(i)
            
            # Stop when the term becomes smaller than the precision limit (evaluates to 0)
            if delta == 0:
                break
                
            result += sign * delta
            sign = -sign
            i += 2
            
            # Visual progress print for every 1000 terms
            if i % 1001 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()
                
        return result

    print("[STATUS] Running Machin's Formula series expansion...", end="")
    # pi = 4 * (4 * arccot(5) - arccot(239)) * 4 -> pi = 16 * arccot(5) - 4 * arccot(239)
    pi = Decimal(4) * (Decimal(4) * arccot(5) - arccot(239))
    print(" Done!")
    
    # Apply exact rounding to the requested digits
    getcontext().prec = digits
    return +pi

def main():
    digits = 10000
    start_time = time.time()
    
    # Calculate Pi
    pi_value = calculate_pi(digits)
    
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    print("\n" + "="*50)
    print(f"[SUCCESS] Calculated {digits} digits of Pi!")
    print(f"[TIME] Calculation time: {elapsed_time:.4f} seconds")
    print("="*50)
    
    # Preview first 100 digits
    pi_str = str(pi_value)
    print(f"\nPreview (First 100 digits):\n{pi_str[:102]}...")
    
    # Save the entire 10,000 digits to a text file
    output_filename = "pi_10k.txt"
    try:
        with open(output_filename, "w") as f:
            f.write(pi_str)
        print(f"\n[INFO] Saved all {digits} digits to file: {output_filename}")
    except Exception as e:
        print(f"[ERROR] Failed to save file: {e}")

if __name__ == "__main__":
    main()
