""" S3-T-Display is finicky and can lock up forever w/o a short sleep  """
try:

    import time
    print("Sleeping")
    time.sleep(2)
    import smain
    
except Exception as e:
    print(str(e))
