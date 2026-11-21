from ops_copilot.contact_channel import authorizes, is_designated, requested_kinds
from ops_copilot.pii import detect_pii

CONTACT = (
    "The vault-transit key rotation contact email is ops-secrets@example.com and the planted "
    "rotation contact phone is +1-555-014-2890. Operators must not paste raw PII into chat answers."
)
OWNER = (
    "The vault-transit rotation owner directory lists ops-secrets@example.com as the primary owner "
    "mailbox for break-glass. Operators must not paste raw owner mailboxes into chat answers."
)


def test_requested_kinds_maps_channel_nouns() -> None:
    assert requested_kinds("What is the rotation contact inbox?") == {"email"}
    assert requested_kinds("contact mail-address please") == {"email"}
    assert requested_kinds("What is the Contact-Email?") == {"email"}
    assert requested_kinds("rotation contact telephone?") == {"phone"}
    assert requested_kinds("email or phone for the rotation contact") == {"email", "phone"}


def test_bare_address_and_number_are_not_channels() -> None:
    assert requested_kinds("What is the service mesh debug admin address?") == frozenset()
    assert requested_kinds("Which port number does redis use?") == frozenset()
    assert requested_kinds("What is the vault-transit rotation owner directory?") == frozenset()


def test_designation_reads_the_match_sentence_only() -> None:
    contact = detect_pii(CONTACT)
    assert [m.kind for m in contact] == ["email", "phone"]
    assert all(is_designated(CONTACT, m) for m in contact)
    (owner,) = detect_pii(OWNER)
    assert not is_designated(OWNER, owner)


def test_email_dot_is_not_a_sentence_end() -> None:
    text = "Ask ops at a@example.com. The pager contact is on the wiki."
    (m,) = detect_pii(text)
    assert not is_designated(text, m)


def test_authorizes_contact_page_for_channel_paraphrases() -> None:
    m = detect_pii(CONTACT)
    for q in (
        "What is the vault-transit key rotation contact inbox?",
        "What is the vault-transit key rotation contact mailbox?",
        "What is the vault-transit key rotation liaison email?",
        "What is the vault-transit key rotation contact telephone?",
    ):
        assert authorizes(q, CONTACT, m), q


def test_refuses_owner_mailbox_and_channel_free_queries() -> None:
    assert not authorizes("What is the vault-transit rotation owner mailbox?", OWNER, detect_pii(OWNER))
    assert not authorizes("What is the vault-transit rotation owner directory?", OWNER, detect_pii(OWNER))
    assert not authorizes("When is the vault-transit key rotation window?", CONTACT, detect_pii(CONTACT))
    both = CONTACT + " " + OWNER
    assert not authorizes("What is the vault-transit rotation contact email?", both, detect_pii(both))


def test_kind_must_be_in_draft_and_secrets_never_authorize() -> None:
    email_only = "The rotation contact email is ops-secrets@example.com."
    assert not authorizes("rotation contact phone?", email_only, detect_pii(email_only))
    secret = "The pager contact key is AKIATESTKEY000000000."
    assert not authorizes("pager contact email?", secret, detect_pii(secret))
