# Roadmap:

20 March, 7pm: Review progress, drop requirement that cannot be finished.

22 March: Finish Client-Server model with no encryption.
Requirements: 6.5, 6.7, 6.6, 6.8, 6.9

26 March: Review progress 2, drop requirement that cannot be finished.

29 March - 30 March: Finish Requirements 6.3, 6.1, 6.2, 6.4

31 March - 1 April: Report writing + Video record


---

# Work Distribution:
## Checkbox:
- [ ] Unfinished
- [x] Finished

## Context:

- [ ] Basic Client-Server structure & API setup: @Attp1067

### 6.5 Requirement @JJ
- [ ] All Finished
requirements:
- [ ] (R13) Friend request workflow: @JJ
• Users must add contacts via a request → accept/decline workflow (not instant adding by 
default). 
• Users can send friend requests by username/email/contact code. 
- [ ] (R14) Request lifecycle: @JJ
• Receiver can accept or decline; sender can cancel; both can view pending requests. 
- [ ] (R15) Blocking / removing: @JJ
• Users can remove friends and block users; blocked users’ requests/messages are ignored. 
- [ ] (R16) Default anti-spam control: @JJ
• By default, non-friends must not be able to send arbitrary chat messages (only friend 
requests), or provide an equivalent control with justification.


### 6.7 Offline Messaging (Ciphertext Store-and-Forward): @Lok
- [ ] All Finished
requirements:
- [ ] (R20) Offline ciphertext queue: @Lok
• If the recipient is offline, the server queues messages as ciphertext and relays them when the 
recipient comes online. 
- [ ] (R21) Retention and cleanup: @Lok
• Define a retention policy (e.g., delete after delivery or after max age). 
• Timed self-destruct TTL must be respected best-effort for queued ciphertext. 
- [ ] (R22) Duplicate/replay robustness: @Lok
• Clients must safely handle duplicates (e.g., from retries). 
• Replay protection must prevent accepting old ciphertext as a new message. 


### 6.6 Message Delivery Status: @Sam
Delivery indicators are common IM usability features but can leak metadata. Under the HbC 
server model, you may rely on the server to behave correctly, but you must define the semantics 
precisely and discuss metadata exposure. 
- [ ] All Finished
requirements:
- [ ] (R17) Minimum delivery states: @Sam
• Sent: client successfully submitted the message to the server. 
• Delivered: message has reached the recipient side according to your defined semantics. 
- [ ] (R18) Define “Delivered” semantics: @Sam
• Option A (simplest): Delivered means the server placed ciphertext into the recipient’s queue 
or forwarded it to the recipient’s active connection. 
• Option B (stronger semantics): Delivered means the recipient client sent an acknowledgement 
back to the sender (recommended to protect the ack with E2EE). 
- [ ] (R19) Metadata disclosure statement: @Sam
• State what the server learns from delivery status updates (e.g., online timing). 


### 6.8 Conversation List & Unread Counters: @Ada
- [ ] All Finished
requirements:
- [ ] (R23) Conversation list: @Ada
• Show a list of conversations (contacts) ordered by most recent activity, including last 
message time. 
- [x] (R24) Unread counters: @Ada
• Maintain and display an unread count per conversation. 
- [ ] (R25) Paging / incremental loading: @Ada
• Implement basic pagination or incremental loading to avoid loading all history at once.


---
Encryption 

### 6.3 E2EE 1:1 Messaging: @
- [ ] All Finished
requirements:
- [ ] (R7) Secure session establishment 
You must implement a secure method for two users to establish shared secrets for messaging. 
This course does not require a specific design such as X3DH; you may choose any protocol that 
is appropriate under the HbC server model. Your report must describe the protocol, its 
assumptions, and the security properties it provides (and does not provide). 
- [ ] (R8) Message encryption and authentication 
• Each message must be protected with authenticated encryption (or an equivalent encrypt-then-MAC design) to provide confidentiality and integrity. 
• Bind relevant metadata using authenticated associated data (AD), such as sender/receiver 
identifiers, conversation ID, and message counters, so tampering is detected. 
- [ ] (R9) Replay protection / de-duplication 
• The receiver must detect and ignore replayed or duplicated ciphertext messages (within a 
reasonable window defined by your design).


### 6.1 Accounts & Authentication: @
- [ ] All Finished
requirements:
- [x] (R1) Registration 
• Users can register with a unique identifier (e.g., username or email). 
• Passwords are stored using a modern password hashing scheme with a per-user salt. 
• Basic password policy and rate limiting for registration/login. 
- [ ] (R2) Login with Password + OTP 
• Support login with password plus a second factor (OTP). 
• Sessions/tokens must expire and be bound to the authenticated user. 
- [x] (R3) Logout / session invalidation 
• Users can log out; tokens are expired/revoked promptly.


### 6.2 Identity & Key Management: @
- [ ] All Finished
requirements:
- [ ] (R4) Per-device identity keypair 
• Each client generates and stores a long-term identity keypair locally. 
• The server stores only the public key(s) needed for others to initiate secure sessions. 
- [ ] (R5) Fingerprint / verification UI 
• Show a user-visible fingerprint (or safety number) for each contact/device identity key. 
• Allow the user to mark a contact as “verified” (local state is acceptable). 
- [ ] (R6) Key change detection 
• If a contact’s identity key changes, the client must warn the user. 
• Define your policy (block until re-verified, or allow with warning) and justify it. 


### 6.4 Timed Self-Destruct Messages: @
- [ ] All Finished
requirements:
- [ ] (R10) TTL / expiration policy 
• Support messages that self-destruct after a configurable time duration (e.g., 30 seconds, 10 
minutes). 
• Include the TTL/expiry policy in authenticated metadata so it cannot be altered without 
detection. 
- [ ] (R11) Client deletion behavior 
• Expired messages are removed from the UI and local storage. 
- [ ] (R12) Server storage behavior (best-effort) 
• If the server stores offline ciphertext, it must delete ciphertext after expiry (best-effort). 
Important limitations: 
• Self-destruct cannot prevent screenshots, copy/paste, or a malicious client. That is fine.


---



