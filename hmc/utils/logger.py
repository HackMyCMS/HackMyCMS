import logging
 
setattr(logging, "RESULT", 35)

class HMCLogger(logging.Logger):
    def success(self, msg:str, *args) -> None:
        if self.isEnabledFor(logging.RESULT):
            print("[*]", msg % args)
    
    def failure(self, msg:str, *args) -> None:
        if self.isEnabledFor(logging.RESULT):
            print("[x]", msg % args)

logging.setLoggerClass(HMCLogger)
log = logging.getLogger("hmc")
log.setLevel(logging.RESULT)

formatter = logging.Formatter('[-] %(asctime)s - %(levelname)s: %(message)s')
ch = logging.StreamHandler()
ch.setFormatter(formatter)
log.addHandler(ch)
