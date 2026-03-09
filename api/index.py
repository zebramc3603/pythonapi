from fastapi import FastAPI
app = FastAPI()
@app.get("/")
def read_root():
    myresp = {"message", "Hello from FastAPI on Vercel!"}
    return myresp

@app.get("/api/health")
def health_check():
    myresp = {"status", "healthy"}
    return myresp
