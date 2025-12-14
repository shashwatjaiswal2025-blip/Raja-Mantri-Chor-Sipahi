# Raja-Mantri-Chor-Sipahi
Codechef interview project 2
We Use FastAPI for baackend and UUID for generating the room and player ID
The codumentation can be checked at /docs after starting the server
the server can be started by running the  command "py -m uvicorn main:app --reload" at the terminal pointing to the venv.
there are 2 more additional HTML equest to check all the list of rooms and to Reset the assigned roles after getting the result
This can be usefull in testing: https://shashwatj0107-9790495.postman.co/workspace/Personal-Workspace~ac403138-74dd-414e-bf85-2eeb399d9f30/collection/48426681-4cb1bcba-8116-42ce-a5d2-da41604c90f4?action=share&creator=48426681

I have modified the suggested API endpoints from /room to /rooms everywhere for uniformity

Possible improvements in future:
1) add the authentication system to the header to auto verify the players
2) add a requestn to kick people out of the room to get th peopl in waiting list into the room. make it so only the creator of the room can do this
