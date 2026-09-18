[← Back to main table of contents](../README.md)

# 14. Account and Information Security

Scope: money and personal information. When someone else takes over your accounts, what you lose is money, the people in your contact list, and your identity.
### 1. Turn on two-step verification for email, payment, and social accounts — prefer on-device prompts, with SMS codes as the fallback
<!-- 成本标签: 钱=0 时间=少 毅力=否 收益=大 口径=金钱 -->
- Cost: 0 yuan; set up once per account, two to three minutes
- In plain terms: on-device prompts block over ninety percent of phishing-based account takeovers and all automated ones, while question-based checks like "where did you last log in" or a backup email stop only about a tenth of phishing takeovers. You set it up once, in a few minutes.
- Benefit: Google's review of 350,000 real hijacking attempts found that device-based verification (on-device prompts, security keys) blocked "more than 94% of phishing-based hijack attempts and 100% of automated hijack attempts," while knowledge-based verification (asking about your last login location, backup email, and the like) "blocked as little as 10% of phishing hijacks and 73% of automated hijacks"
- Evidence grade: A
- Sources: Doerfler P, Thomas K, Marincenko M, et al. (2019). Evaluating Login Challenges as a Defense Against Account Takeover. The World Wide Web Conference (WWW '19). <https://doi.org/10.1145/3308558.3313481>
- Notes: the same study also found that verification locks out legitimate users: 52% failed to sign in on the first try, though 97% eventually got in. Start with email, because every other account can recover its password through it

### 2. Use a separate password for your email, never reused on any website
<!-- 成本标签: 钱=0 时间=少 毅力=些 收益=大 口径=金钱 -->
- Cost: 0 yuan; with a password manager you don't have to remember it
- In plain terms: passwords leaked from other sites get tried directly against your email. Once someone gets into your email, every account that can recover its password through it goes down with it.
- Benefit: credential stuffing is the laziest form of attack: a password leaked elsewhere is tried straight against your email, and once the email falls, every account that uses it for password recovery falls with it
- Evidence grade: C
- Sources: 作者经验，无直接文献
- Notes: if you can't remember it, use your browser's built-in password manager — far better than reusing one password. Don't store passwords in WeChat favorites or a notes app

### 3. Set a lock-screen password on your phone and a PIN code on your SIM card
<!-- 成本标签: 钱=0 时间=少 毅力=否 收益=大 口径=金钱 -->
- Cost: 0 yuan; set up once
- In plain terms: if your phone is lost, the fastest move for whoever finds it is to put the SIM card into another phone to receive verification codes, then reset your accounts one by one. With a PIN on the SIM card, the phone demands the password at startup on a new device, and that path is cut off entirely.
- Benefit: after a phone is lost, the fastest attack path is to put the SIM card into another phone to receive SMS verification codes, then reset accounts one by one. With a PIN on the SIM card, the phone demands the password at startup on a new device, and this path is cut off entirely
- Evidence grade: C
- Sources: 作者经验，无直接文献
- Notes: the PIN is set under the phone's "SIM card lock" setting; the factory default is usually 1234 or 0000, and three wrong entries require a PUK code to unlock — write it down right after you set it

### 4. If your phone is lost, act in this order: report the SIM lost, lock remotely, change passwords, file a police report, freeze bank cards
<!-- 成本标签: 钱=0 时间=少 毅力=否 收益=大 口径=金钱 -->
- Cost: 0 yuan; a dozen or so minutes
- In plain terms: the order matters more than how fast you move: first report the SIM card lost to cut off the verification codes that everything depends on, then lock and wipe the phone remotely, then change your email and payment passwords from a computer, then file a police report and keep the receipt, and finally freeze bank cards as needed. You can also report the SIM lost by calling your carrier's customer service from someone else's phone.
- Benefit: order matters more than speed: reporting the SIM lost first cuts off the verification-code lifeline, then remotely lock and wipe the device, then change email and payment passwords from a computer, then file a police report and keep the receipt, and finally freeze bank cards as needed
- Evidence grade: C
- Sources: 作者经验，无直接文献；补办身份证见第 7 节，冒名贷款见第 8 节关于征信的一条
- Notes: memorize in advance the customer service numbers of the three major carriers (China Mobile 10086, China Unicom 10010, China Telecom 10000) and the region your phone number is registered in. Reporting the SIM lost by calling customer service from another person's phone also works

### 5. When a card is fraudulently used, report it lost and freeze it before filing a police report, then demand the bank compensate you: proving "the cardholder made the transaction" is the bank's responsibility
<!-- 成本标签: 钱=0 时间=少 毅力=些 收益=大 口径=金钱 -->
- Cost: 0 yuan; report the card lost or freeze it the moment you spot suspicious activity, and keep the police report, the loss-report record, and the transaction notifications; if the card is still on you, make a small balance inquiry or deposit/withdrawal nearby to establish where the real card was
- In plain terms: when your card is fraudulently used, you don't have to prove "it wasn't me"; it's the other way around — the bank has to produce evidence that the transaction was made by you or authorized by you, and if it can't, it has to pay: for a debit card, the stolen deposits with interest plus your losses; for a credit card, the deducted overdraft must be returned and the bank cannot demand that money back from you, and any adverse credit record must be removed. The precondition is freezing the card the moment you spot the activity: drag your feet and the additional losses that pile up are yours to bear; if you handed over your password or verification codes, you also carry part of the responsibility.
- Benefit: the Supreme People's Court's provisions on bank card civil disputes divide the burden of proof: a cardholder claiming counterfeit-card fraud or online fraud can prove it with effective legal documents, the location of the real card at the time of the transaction, the place where the transaction occurred, the account transaction details, transaction notifications, police reports, loss-report records, and the like; **when the card issuer or a non-bank payment institution claims the transaction was made by the cardholder or with the cardholder's authorization, it bears the burden of proof**. If, after you notify the bank, the bank fails to verify in time or fails to provide or preserve transaction receipts or surveillance footage, leaving the evidence unobtainable, the bank bears the consequences of being unable to meet its burden of proof. Once the claim is established: a debit cardholder can demand the issuer pay the fraudulently withdrawn deposits with principal and interest and compensate the losses; a credit cardholder can demand the return of the deducted overdraft with principal and interest plus penalty fees and compensation for losses, and if the bank in turn demands that the cardholder repay the overdraft, the court will not support it. The cardholder can also demand that the issuer promptly remove the corresponding adverse credit records (nationwide, in effect from May 25, 2021)
- Evidence grade: A
- Sources: 最高人民法院 (2021). 关于审理银行卡民事纠纷案件若干问题的规定（第四、五、七、十四、十五条）. <https://www.court.gov.cn/fabu/xiangqing/304771.html>
- Notes: two situations shift responsibility onto you: one, if you are "at fault for failing to properly safeguard" identity-verification information and transaction-verification information such as the bank card, password, and verification codes, you bear responsibility proportionate to your fault — so don't share passwords and don't forward verification codes (see item 1); two, if delayed reporting the loss enlarged the losses, you bear the enlarged portion, so the first step is always to report and freeze, not to argue with customer service. The same rules apply to third-party payment institutions, and if their promotional materials promised "advance compensation" in a concrete and specific way, you can demand they pay first on that basis. Money you were tricked into transferring yourself is a different path — see Section 8, item 2.

### 6. Check your accounts' logged-in devices and authorized apps every so often, and clear out the ones you don't use
<!-- 成本标签: 钱=0 时间=少 毅力=些 收益=中 口径=金钱 -->
- Cost: 0 yuan; a few minutes each time
- In plain terms: account thieves often lurk for a while before striking. Unfamiliar devices in the logged-in device list and long-abandoned third parties in the authorized-app list are traces an ordinary person can see on their own — when you see one, sign out everywhere and change the password.
- Benefit: account takeover usually doesn't erupt on the spot; the attacker lurks first. Unfamiliar devices in the logged-in device list and long-abandoned third parties in the authorized-app list are the easiest traces to spot
- Evidence grade: C
- Sources: 作者经验，无直接文献
- Notes: WeChat, Alipay, email, and Apple and Android accounts all have this entry point. If you find an unfamiliar device, sign out everywhere and change the password

### 7. Don't tap "agree to all" just to use an app: for information that isn't necessary, refusing to share it cannot be grounds to deny you the service
<!-- 成本标签: 钱=0 时间=少 毅力=些 收益=中 口径=自由 -->
- Cost: 0 yuan; the price is resisting the urge to tap "agree to all"
- In plain terms: if the information isn't necessary for providing the service, the provider cannot lock you out for declining to share it; and what they collect must stay limited to the minimum they actually need. A map app needing your location is necessary; a flashlight app needing your contact list is not.
- Benefit: the law states explicitly that no provider may refuse to supply a product or service on the grounds that the individual did not consent to or withdrew consent for the processing of personal information, except where the processing is necessary for providing the service; collection must be limited to the smallest scope necessary to achieve the processing purpose
- Evidence grade: A
- Sources: 全国人大常委会 (2021). 个人信息保护法. 中国人大网. <http://www.npc.gov.cn/npc/c2/c30834/202108/t20210820_313088.html>：第六条「收集个人信息，应当限于实现处理目的的最小范围，不得过度收集个人信息」；第十六条「个人信息处理者不得以个人不同意处理其个人信息或者撤回同意为由，拒绝提供产品或者服务；处理个人信息属于提供产品或者服务所必需的除外」；第十五条「基于个人同意处理个人信息的，个人有权撤回其同意。个人信息处理者应当提供便捷的撤回同意的方式」
- Notes: the test is "is this information necessary for providing this service": a map app needing your location is necessary, a flashlight app needing your contact list is not. After installing an app, go straight into the system's app-permissions page and switch off everything not necessary, granting one-time permission when it's actually needed.

### 8. You have the right to view, copy, correct, and delete your own personal information, and you can sue if you're refused
<!-- 成本标签: 钱=0 时间=少 毅力=些 收益=中 口径=自由 -->
- Cost: 0 yuan; complaining or suing only becomes necessary if they stall; a real lawsuit is a matter of months at minimum with lawyer's fees on you, so complaining first is the better deal
- In plain terms: you can demand that a company let you view, copy, correct, and delete your own information; when the service ends, the retention period expires, or you withdraw consent, the company is supposed to delete on its own initiative. Any refusal of your request must come with stated reasons, and if they don't act you can go straight to court. Deleting an account and deleting your information are two different things — after cancelling the account you have to ask for deletion separately.
- Benefit: when the service stops, the retention period expires, consent is withdrawn, or the purpose has been fulfilled, the company must delete proactively; if it hasn't, you can demand deletion; any refusal of a request to exercise your rights must state its reasons, and you can sue directly in court
- Evidence grade: A
- Sources: 全国人大常委会 (2021). 个人信息保护法. 中国人大网. <http://www.npc.gov.cn/npc/c2/c30834/202108/t20210820_313088.html>：第四十五条「个人有权向个人信息处理者查阅、复制其个人信息……个人请求查阅、复制其个人信息的，个人信息处理者应当及时提供」；第四十六条更正、补充权；第四十七条列了五种应当主动删除的情形，含「（一）处理目的已实现、无法实现或者为实现处理目的不再必要」「（二）个人信息处理者停止提供产品或者服务，或者保存期限已届满」「（三）个人撤回同意」，「个人信息处理者未删除的，个人有权请求删除」；第五十条「个人信息处理者应当建立便捷的个人行使权利的申请受理和处理机制。拒绝个人行使权利的请求的，应当说明理由」「个人可以依法向人民法院提起诉讼」
- Notes: cancelling an account and deleting personal information are two separate things; after cancellation, request deletion separately. Before switching or selling an old phone, sign out of all accounts and unbind them on the old device first, then factory-reset it — the law gives you the right to deletion after the fact; it cannot pull back what has already leaked.

### 9. Face recognition is not something you must accept: when alternatives exist, you cannot be forced to use only your face, and if you refuse, other methods must be offered
<!-- 成本标签: 钱=0 时间=少 毅力=些 收益=中 口径=金钱 -->
- Cost: 0 yuan; when asked for a face scan, ask "is there another verification method," and if there isn't, demand one
- In plain terms: as long as other means can achieve the same goal, face recognition cannot be made the only option; if you decline a face scan, they must offer an alternative such as a card, a password, or your ID card, and they cannot strong-arm you by claiming "we can't process this." In private spaces such as hotel guest rooms, public bathhouses, changing rooms, and restrooms, no one may install facial-recognition equipment. The biggest difference between your face and a password is that a face can't be changed once it leaks.
- Benefit: the security management measures for facial recognition technology state: "Where other non-facial-recognition methods exist to achieve the same purpose or meet the same business requirements, facial recognition technology must not be used as the sole verification method. If an individual does not consent to identity verification through facial information, other reasonable and convenient methods shall be provided." "No organization or individual may mislead, deceive, or coerce an individual into accepting facial-recognition verification of identity on the grounds of handling business or improving service quality." Where facial information is processed on the basis of individual consent, "separate consent given voluntarily and explicitly under conditions of full knowledge" must be obtained; the individual has the right to withdraw consent and the processor must provide a convenient way to withdraw; processing the facial information of minors under fourteen requires the consent of a parent or other guardian. Facial-recognition equipment installed in public places "must be necessary for maintaining public safety" and carry prominent notice signs; inside private spaces within public places — hotel guest rooms, public bathhouses, public changing rooms, public restrooms — no organization or individual may install such equipment. Except where laws or administrative regulations provide otherwise or separate consent has been obtained, facial information must be stored within the facial-recognition device itself and must not be transmitted externally over the internet (nationwide, in effect from June 1, 2025)
- Evidence grade: A
- Sources: 国家互联网信息办公室、公安部 (2025). 人脸识别技术应用安全管理办法（第 19 号令，第十条、十二条、十三条，2025 年 6 月 1 日起施行）. <https://www.cac.gov.cn/2025-03/21/c_1744174262156096.htm>
- Notes: the most common encounters are residential-compound gates, rental platforms, gyms, and hotels demanding a face recording. When told "the system only supports face recognition," read the quoted passage above to them and demand an alternative such as a card, a password, or an ID card; if they still refuse, report it to the local cyberspace administration. Where the state has separate provisions on facial-recognition identity verification (some finance and government-service scenarios), those provisions govern. The biggest difference between your face and a password is that a face can't be changed once it leaks, so it deserves more caution than a password. Processors whose stored data reaches 100,000 people must file with the cyberspace administration at the provincial level or above within 30 working days — also a good question for judging whether the other party is operating properly. Your rights to view, correct, and delete your personal information are covered in item 8.
