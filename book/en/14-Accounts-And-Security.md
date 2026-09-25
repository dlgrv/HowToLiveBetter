# 14. Account and Information Security

Backlink: [← Return to main index](../README.md)

Protecting your money and personal data is essential. If someone gains access to your accounts, they can steal funds right away. They may also use your account to scam people on your contact list. In short, your identity becomes vulnerable too.
### 1. Enable two-factor authentication on email, payment, and social accounts; prioritize phone pop-ups over SMS codes
<!-- 成本标签: 钱=0 时间=少 毅力=否 收益=大 口径=金钱 -->
- Cost: No cost involved. Each account takes just two to three minutes to set up once.
- In plain terms: Two-factor authentication means an extra verification step beyond the password when logging in. Using a pop-up prompt on your phone that requires a single tap to confirm blocks over 90% of phishing and account theft attempts. In contrast, older verification methods such as answering questions like “Where did you log in last time?” or “What is your backup email?” only block around 10% of such attacks.
- Benefit: Google analyzed 350,000 real-world account hijacking attempts. For authentication methods relying on device verification — such as phone pop-ups or physical security keys — over 94% of phishing-related hijacking attempts and 100% of automated hijacking attempts were prevented. These automated attempts involve bots using leaked passwords to try logging into accounts in bulk. For verification based on answering personal questions, only 10% of phishing attempts and 73% of automated attempts were blocked.
- Evidence grade: A
- Notes: The same study also found that these verification methods occasionally block legitimate users from accessing their accounts. 52% of real users failed to log in on their first try. However, 97% of them eventually gained access. It is recommended to enable this feature on email accounts first, as most other accounts allow password recovery via email.
- Sources:Doerfler P, Thomas K, Marincenko M, et al. (2019). Evaluating Login Challenges as a Defense Against Account Takeover. The World Wide Web Conference (WWW '19). <https://doi.org/10.1145/3308558.3313481>

### 2. Use a unique password solely for your email
<!-- 成本标签: 钱=0 时间=少 毅力=些 收益=大 口径=金钱 -->
- Cost: No cost involved. Storing it in a password manager eliminates the need to memorize it. The real challenge lies in breaking the old habit of reusing one password across multiple sites.
- In plain terms: If a password you use elsewhere gets stolen, attackers can use it to log straight into your email account. Once they gain access to your email, they can reset passwords for any other accounts linked to it. Therefore, your email password must be unique and never reused anywhere else.
- Benefit: Credential stuffing is one of the easiest attack methods: attackers simply test stolen passwords against other accounts. If your email password is compromised, all accounts that rely on it for password recovery become vulnerable too. The US Cybersecurity and Infrastructure Security Agency recommends using a distinct, strong password of at least 16 characters for every account, and storing it via a password manager.
- Evidence grade: C
- Notes: If you struggle to memorize passwords, use the built-in password manager in your web browser. It stores passwords for each site for you, which is far safer than reusing the same password everywhere. Avoid saving passwords in WeChat favorites or note-taking apps.
- Sources:US CISA. Use Strong Passwords. <https://www.cisa.gov/secure-our-world/use-strong-passwords>

### 3. Set a screen lock on your phone and a PIN for the SIM card
<!-- 成本标签: 钱=0 时间=少 毅力=否 收益=大 口径=金钱 -->
- Cost: No cost at all. You only need to set the screen lock and the SIM PIN once each.
- In plain terms: The SIM card is that tiny card inside your phone that receives SMS verification codes. If your phone gets lost, a finder can remove the card and insert it into another phone to receive those codes, then reset all your accounts one by one. Setting a PIN on the SIM card means that whenever the card is moved to another phone, the user must enter that PIN before the phone can be used — effectively blocking that path.
- Benefit: Without a SIM PIN, a finder can easily move your SIM card to another phone, receive verification codes, and reset all your accounts. With a PIN in place, that entire process is prevented, keeping your accounts safe even if your phone is lost.
- Evidence grade: C
- Notes: You can set the SIM PIN under “SIM card lock” in your phone settings. The default factory codes are usually 1234 or 0000. If you enter the wrong code three times in a row, you’ll need the PUK code provided by your carrier to unlock it. After setting the PIN, be sure to write it down somewhere safe.
- Sources:作者经验，无直接文献

### 4. Follow these steps if you lose your phone: block the SIM card, remotely lock it, change passwords, file a police report, and freeze your bank cards if needed.
<!-- 成本标签: 钱=0 时间=少 毅力=否 收益=大 口径=金钱 -->
- Cost: No cost involved. Completing all steps takes just a few minutes.
- In plain terms: The order of actions matters more than speed. First, block the SIM card to cut off access to verification codes. Next, remotely lock the phone. Then, use a computer to change your email and payment passwords. After that, file a police report to obtain a receipt. Finally, freeze your bank cards as needed. Even if you’re using someone else’s phone, you can still call your carrier to block the SIM card.
- Benefit: Following the correct sequence is more important than acting quickly. Step one is blocking the SIM card, which severs the main channel for verification codes. Step two involves remotely locking the phone and erasing all its contents. Step three requires changing your email and payment passwords from a computer. Step four is filing a police report to get a receipt. Finally, freeze your bank cards if necessary. The Federal Communications Commission also advises that even if you believe you merely misplaced your phone, you should still remotely lock it. If it’s stolen, file a police report immediately, providing the phone’s model and IMEI number, and inform your carrier right away.
- Evidence grade: C
- Notes: Save the customer service numbers for all three major carriers in advance: China Mobile at 10086, China Unicom at 10010, and China Telecom at 10000. Also note the city where you registered your phone number, as customer service agents will ask for this information. You can still call carrier hotlines from someone else’s phone to block your SIM card.
- Sources:US FCC. Protect Your Smart Device. <https://www.fcc.gov/consumers/guides/protect-your-mobile-device>；步骤顺序是作者经验；补办身份证见第 7 节，冒名贷款见第 8 节关于征信的一条

### 5. If your card is fraudulently used, report it and freeze the card first, then demand compensation from the bank: proving “you made the transaction” is the bank’s responsibility
<!-- 成本标签: 钱=0 时间=少 毅力=些 收益=大 口径=金钱 -->

- Cost: No cost at all. As soon as you notice anything suspicious on your card statements, immediately report it and freeze the card. Keep all records: police reports, freeze confirmations, and transaction notifications from the bank. If the card is still in your possession, make a small inquiry or deposit nearby to create a record proving you had the card with you at the time of the fraud. The hardest part is resisting the urge to argue with customer service first — always freeze the card first.

- In plain terms:  
  If someone fraudulently uses your card, you don’t have to prove “this wasn’t me.” Instead, it’s the bank’s duty to prove the transaction was made by you. If they can’t, they must compensate you. This only applies if you report and freeze the card right away. Delaying this step means you’ll bear any additional losses that occur afterward.

- Benefit:  
  Supreme Court rulings clearly define who must provide evidence. If you claim the transaction resulted from counterfeit card fraud or online fraud, you must first gather proof — such as official legal documents, records showing where the card was physically located at the time, transaction logs, notifications, police reports, and freeze confirmations. Conversely, if the issuing bank or any third‑party payment service insists the transaction was authorized by you, they must produce evidence to support that claim. If, after you notify the bank, it fails to verify the transaction promptly or to preserve transaction records and surveillance footage, the bank bears the consequences of lacking proof. Once proven, debit‑card holders may demand full reimbursement of stolen funds plus compensation for any losses; credit‑card users may request a refund of all unauthorized charges, interest, and penalties, and courts will reject any demand that the cardholder repay those amounts. You may also ask the bank to promptly remove any resulting negative credit entries (effective 25 May 2021).

- Evidence grade: A

- Notes: There are two situations where you remain liable. First, if you fail to protect your card, PIN, or verification codes — in other words, if you neglect your duty to safeguard them — you’ll bear part of the loss. Keep your PIN secret and never share verification codes (see Item 1; two‑factor authentication via phone alerts is preferred). Second, if you delay reporting and freezing the card, any extra losses incurred afterward are your responsibility. Hence, the very first step is always to freeze the card — don’t waste time arguing with customer service first. These rules also apply to third‑party payment services. If such a service advertises “immediate compensation” with clear terms, you may demand payment from them. If you were tricked into transferring money, that falls under a separate procedure; see Item 8.2: call 110 or 96110 immediately to request a stop‑payment order.
- Sources:最高人民法院 (2021). 关于审理银行卡民事纠纷案件若干问题的规定（第四、五、七、十四、十五条）. <https://www.court.gov.cn/fabu/xiangqing/304771.html>

### 6. Periodically check the devices logged into your account and any authorized apps, then remove the ones you no longer use
<!-- 成本标签: 钱=0 时间=少 毅力=些 收益=中 口径=金钱 -->
- Cost: No cost at all. It only takes a few minutes each time. The hard part is that there’s no reminder — you have to remember to do it yourself.
- In plain terms: “Logged-in devices” refer to the phones and computers that can still access your account right now. Account thieves often lie low for a while before making their move. If you see any unfamiliar devices on the list, or third-party apps you no longer use still linked to your account, log out from all devices and change your password right away.
- Benefit: Account theft rarely happens instantly — attackers usually spend some time lurking first. The list of logged-in devices shows all phones and computers currently able to access your account, while the list of authorized apps shows all third-party services you’ve given permission to log in using your account. Any unknown devices or unused third-party apps on these lists are the easiest clues to spot.
- Evidence grade: C
- Notes: This feature is available in WeChat, Alipay, email accounts, Apple ID, and Android accounts. If you spot any unfamiliar devices, simply log out from all devices and change your password.
- Sources:作者经验，无直接文献

### 7. Don’t tap “Allow all” just to use an app: the data isn’t mandatory, and refusing to share it won’t block service access
<!-- 成本标签: 钱=0 时间=少 毅力=些 收益=中 口径=自由 -->

- Cost: No cost involved. The hard part is resisting the urge to tap “Allow all.”
- In plain terms: Apps request your data. If that data isn’t strictly necessary to deliver the service, the app can’t deny you access just because you refuse to share it. It may only collect what it actually needs. For instance, a map app needs your location, but a flashlight app has no business asking for your contacts list.
- Benefit: Two key legal points apply here. First, providers may not deny products or services on the grounds that a user hasn’t consented or has withdrawn consent — unless processing that data is genuinely essential to delivering the service. Second, data collection must stay limited to what’s absolutely required for the intended purpose; only the minimal amount needed may be gathered.
- Evidence grade: A
- Notes: The deciding factor is simple: is this data truly essential to providing the service? Location data is essential for a map app, but contact lists aren’t needed for a flashlight app. After installing an app, head to your phone’s settings under app permissions and turn off any nonessential permissions. Grant access only when you genuinely need them, and even then, limit it to a one-time permission.
- Sources:全国人大常委会 (2021). 个人信息保护法. 中国人大网. <http://www.npc.gov.cn/npc/c2/c30834/202108/t20210820_313088.html>：第六条「收集个人信息，应当限于实现处理目的的最小范围，不得过度收集个人信息」；第十六条「个人信息处理者不得以个人不同意处理其个人信息或者撤回同意为由，拒绝提供产品或者服务；处理个人信息属于提供产品或者服务所必需的除外」；第十五条「基于个人同意处理个人信息的，个人有权撤回其同意。个人信息处理者应当提供便捷的撤回同意的方式」

### 8. You have the right to view, copy, correct, and delete your personal information; if refused, you can sue.
<!-- 成本标签: 钱=0 时间=少 毅力=些 收益=中 口径=自由 -->

- Cost: There is no cost involved. Only if the company drags its feet do you need to file a complaint or sue. A lawsuit typically takes several months to resolve, and you must pay legal fees yourself. Therefore, filing a complaint first is the more cost-effective option. The difficult part is having to repeatedly follow up when the company delays action.

- In plain terms: You have the right to demand that a company let you view, copy, correct, and delete your personal information. When a service is discontinued, its retention period expires, or you withdraw consent, the company is obligated to delete that data on its own. If it refuses your request, it must provide a valid reason; otherwise, you can take it to court. Deactivating an account and deleting personal information are two separate actions — after deactivating, you must separately request deletion.

- Benefit: There are several situations in which a company must proactively delete personal information: when a service is discontinued, when the agreed retention period ends, when you withdraw consent, or when the original purpose of data collection has been fulfilled. If it fails to do so, you can demand deletion. Should it deny your rights without justification, you may file a lawsuit.

- Evidence grade: A

- Notes: Deactivating an account and deleting personal information are distinct processes; after deactivating, you must separately request deletion. Before switching phones or selling an old device, make sure to log out of all accounts, unlink them, and then perform a factory reset. The law grants you a right to deletion after the fact — it cannot retrieve data that has already been leaked.
- Sources:全国人大常委会 (2021). 个人信息保护法. 中国人大网. <http://www.npc.gov.cn/npc/c2/c30834/202108/t20210820_313088.html>：第四十五条「个人有权向个人信息处理者查阅、复制其个人信息……个人请求查阅、复制其个人信息的，个人信息处理者应当及时提供」；第四十六条更正、补充权；第四十七条列了五种应当主动删除的情形，含「（一）处理目的已实现、无法实现或者为实现处理目的不再必要」「（二）个人信息处理者停止提供产品或者服务，或者保存期限已届满」「（三）个人撤回同意」，「个人信息处理者未删除的，个人有权请求删除」；第五十条「个人信息处理者应当建立便捷的个人行使权利的申请受理和处理机制。拒绝个人行使权利的请求的，应当说明理由」「个人可以依法向人民法院提起诉讼」

### 9. You’re not required to use facial recognition: if other options exist, they must offer you alternatives if you refuse
<!-- 成本标签: 钱=0 时间=少 毅力=些 收益=中 口径=金钱 -->

- Cost: No cost involved. When asked to use facial recognition, simply ask, “Are there any other verification methods available?” If they claim none exist, demand they provide alternatives. The challenge lies in actually voicing this question on the spot.
- In plain terms: As long as any other method can achieve the same result, a service provider cannot force you to use facial recognition. If you decline facial recognition, they must offer alternatives such as a card swipe, password entry, or ID verification. They also cannot threaten that “the service won’t be provided” if you refuse. Installing facial recognition devices in hotel rooms, public showers, changing rooms, or restrooms is strictly prohibited.
- Benefit: The Administrative Measures for the Safe Use of Facial Recognition Technology clearly state: “Where other non-facial recognition technologies can achieve the same purpose or meet equivalent operational requirements, facial recognition must not be used as the sole verification method. If an individual declines facial recognition for identity verification, other reasonable and convenient alternatives must be provided.” The measures further stipulate: “No organization or individual may mislead, deceive, or coerce individuals into accepting facial recognition for identity verification under the pretext of service delivery or improved quality.” Consent to use facial recognition must be “freely, explicitly, and separately given after full disclosure” — meaning you must be asked specifically about this and must agree independently. You retain the right to withdraw consent, and service providers must offer an easy way to do so. For minors under 14, parental or guardian consent is mandatory. In public spaces, facial recognition devices may only be installed if “necessary for public safety” and must display prominent warning signs. Their use inside private areas such as hotel rooms, showers, changing rooms, or restrooms is forbidden. Facial data must be stored locally on devices and must not be transmitted over the internet, except where permitted by law or with explicit consent (effective nationwide as of June 1, 2025).
- Evidence grade: A
- Notes: Common scenarios include residential building access systems, rental platforms, gyms, and hotels requesting facial data. When they claim “the system only supports facial recognition,” quote the exact wording from the regulations: “Where other non-facial recognition technologies can achieve the same purpose or meet equivalent operational requirements, facial recognition must not be used as the sole verification method.” Then demand alternative verification methods such as card swipes, passwords, or ID checks. If they still refuse, report them to local internet regulatory authorities. Certain financial and government services may have separate rules — follow those instead. Unlike passwords, facial data cannot be changed after a breach, so it demands greater caution. Organizations storing facial data on behalf of 100,000+ individuals must register with provincial or higher-level internet regulators within 30 days; this registration status can help you assess their legitimacy. Your rights to access, correct, or delete your personal data are covered in item 8.
- Sources:国家互联网信息办公室、公安部 (2025). 人脸识别技术应用安全管理办法（第 19 号令，第十条、十二条、十三条，2025 年 6 月 1 日起施行）. <https://www.cac.gov.cn/2025-03/21/c_1744174262156096.htm>
