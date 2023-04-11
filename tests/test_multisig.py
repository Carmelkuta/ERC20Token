import pytest
import brownie

from brownie import RUToken, accounts

from tests.test_tokens import msg, checkFailedTransfer, checkSuccessfulTransfer, deploy_ru_token, mint_ru_tokens, transfer_direct

from scripts.multisig_token import grade_multisig, generate_nonce_and_second_signature_transfer2of3

pytestmark = pytest.mark.skipif(not grade_multisig, reason="Multisig Token not implemented! (Set multisig_token.grade_multisig = True to allow grading)")


def transfer_bysig(tok: RUToken, src, dst, sender, sk, amount):
        nonce,sig = generate_nonce_and_second_signature_transfer2of3(tok, sk, src, dst, amount)
        return tok.transfer2of3(src, dst, amount, nonce, sig.encoded(), msg(sender))


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    pass

@pytest.fixture(scope='module')
def localaccounts():
    return [accounts.add(private_key=bytes([i+1] * 32))  for i in range(10)]


# Globals
price = 100
xfernum = 200 
totalmint = xfernum * 4
maxtok = totalmint * 2


def deploy_and_mint(price, maxtok, totalmint, account):
    tok = deploy_ru_token(price, maxtok, account)
    mint_ru_tokens(tok, account, totalmint)
    return tok

def register_multisigs(tok, localaccounts):
    multisigs = []
    for i in range(len(localaccounts) - 2):
        tx = tok.registerMultisigAddress(localaccounts[i], localaccounts[i+1], localaccounts[i+2])
        multisigs.append(accounts.at(tx.return_value, force=True))
    return multisigs


@pytest.fixture(scope='module')
def deploy_multisigs(localaccounts): 
    l1, l2, l3 = localaccounts[0:3]
    tok = deploy_and_mint(price, maxtok, totalmint, accounts[1])
    multisigs = register_multisigs(tok, localaccounts)
    return tok, multisigs


def test_simple_transfer2of3(localaccounts, deploy_multisigs):
    a1, a2, a3 = accounts[1:4]
    l1, l2, l3 = localaccounts[0:3]
    
    tok, multisigs = deploy_multisigs

    def transfer_bysig_local2(tok: RUToken, src, dst, sender, amount):
        return transfer_bysig(tok, src, dst, sender, l2.private_key, amount)

    checkSuccessfulTransfer(tok, a1, multisigs[0], a1, xfernum, transfer_direct) # Transfer *to* multisig address
    checkSuccessfulTransfer(tok, multisigs[0], a2, l1, xfernum, transfer_bysig_local2) # Transfer *from* multisig address


def test_multiple_register(localaccounts, deploy_multisigs):
    l1, l2, l3 = localaccounts[0:3]
    tok, multisigs = deploy_multisigs
    with brownie.reverts():
        tx = tok.registerMultisigAddress(l1, l2, l3)


def test_multiple_transfer2of3(localaccounts, deploy_multisigs):
    a1, a2, a3 = accounts[1:4]
    l1, l2, l3, l4, l5 = localaccounts[0:5]
    
    tok, multisigs = deploy_multisigs

    def transfer_bysig_local3(tok: RUToken, src, dst, sender, amount):
        return transfer_bysig(tok, src, dst, sender, l3.private_key, amount)

    checkSuccessfulTransfer(tok, a1, multisigs[0], a1, xfernum, transfer_direct) # Transfer *to* multisig address (l1,l2,l3)
    checkSuccessfulTransfer(tok, multisigs[0], multisigs[1], l1, xfernum, transfer_bysig_local3) # Transfer to multisig address (l2,l3,l4)
    checkSuccessfulTransfer(tok, multisigs[1], multisigs[2], l2, xfernum, transfer_bysig_local3) # Transfer *to* multisig address (l3,l4,l5)
    checkSuccessfulTransfer(tok, multisigs[2], multisigs[3], l4, xfernum, transfer_bysig_local3) # Transfer *to* multisig address (l4,l5,l6)


def test_same_address_failed_transfer2of3(localaccounts, deploy_multisigs):
    a1, a2, a3 = accounts[1:4]
    l1, l2, l3, l4, l5 = localaccounts[0:5]
    
    tok, multisigs = deploy_multisigs

    def transfer_bysig_local3(tok: RUToken, src, dst, sender, amount):
        return transfer_bysig(tok, src, dst, sender, l3.private_key, amount)

    checkSuccessfulTransfer(tok, a1, multisigs[0], a1, xfernum, transfer_direct) # Transfer *to* multisig address (l1,l2,l3)
    checkFailedTransfer(tok, multisigs[0], multisigs[1], l3, xfernum, transfer_bysig_local3) # Transfer to multisig address (l2,l3,l4)

def test_bad_sender_transfer2of3(localaccounts, deploy_multisigs):
    a1, a2, a3 = accounts[1:4]
    l1, l2, l3, l4, l5 = localaccounts[0:5]
    
    tok, multisigs = deploy_multisigs

    def transfer_bysig_local3(tok: RUToken, src, dst, sender, amount):
        return transfer_bysig(tok, src, dst, sender, l3.private_key, amount)

    checkSuccessfulTransfer(tok, a1, multisigs[0], a1, xfernum, transfer_direct) # Transfer *to* multisig address (l1,l2,l3)
    checkFailedTransfer(tok, multisigs[0], multisigs[1], l4, xfernum, transfer_bysig_local3) # Transfer to multisig address (l2,l3,l4)


def test_bad_secondsig_transfer2of3(localaccounts, deploy_multisigs):
    a1, a2, a3 = accounts[1:4]
    l1, l2, l3, l4, l5 = localaccounts[0:5]
    
    tok, multisigs = deploy_multisigs

    def transfer_bysig_local4(tok: RUToken, src, dst, sender, amount):
        return transfer_bysig(tok, src, dst, sender, l4.private_key, amount)

    checkSuccessfulTransfer(tok, a1, multisigs[0], a1, xfernum, transfer_direct) # Transfer *to* multisig address (l1,l2,l3)
    checkFailedTransfer(tok, multisigs[0], multisigs[1], l1, xfernum, transfer_bysig_local4) # Transfer to multisig address (l2,l3,l4)


def test_different_secondsig_msgs_transfer2of3(localaccounts, deploy_multisigs):
    a1, a2, a3 = accounts[1:4]
    l1, l2, l3, l4, l5 = localaccounts[0:5]
    
    tok, multisigs = deploy_multisigs

    def transfer_bysig_local2(tok: RUToken, src, dst, sender, amount):
        return transfer_bysig(tok, src, dst, sender, l2.private_key, amount)

    def transfer_bysig_badamount(tok: RUToken, src, dst, sender, amount):
        nonce,sig = generate_nonce_and_second_signature_transfer2of3(tok, l3.private_key, src, dst, amount - 1)
        return tok.transfer2of3(src, dst, amount, nonce, sig.encoded(), msg(sender))

    def transfer_bysig_badsrc(tok: RUToken, src, dst, sender, amount):
        nonce,sig = generate_nonce_and_second_signature_transfer2of3(tok, l3.private_key, a2, dst, amount)
        return tok.transfer2of3(src, dst, amount, nonce, sig.encoded(), msg(sender))

    def transfer_bysig_baddst(tok: RUToken, src, dst, sender, amount):
        nonce,sig = generate_nonce_and_second_signature_transfer2of3(tok, l3.private_key, src, a2, amount)
        return tok.transfer2of3(src, dst, amount, nonce, sig.encoded(), msg(sender))



    checkSuccessfulTransfer(tok, a1, multisigs[0], a1, xfernum, transfer_direct) # Transfer *to* multisig address (l1,l2,l3)
    checkFailedTransfer(tok, multisigs[0], multisigs[1], l1, xfernum, transfer_bysig_badamount) # Transfer to multisig address (l2,l3,l4)
    checkFailedTransfer(tok, multisigs[0], multisigs[1], l1, xfernum, transfer_bysig_badsrc) # Transfer to multisig address (l2,l3,l4)
    checkFailedTransfer(tok, multisigs[0], multisigs[1], l1, xfernum, transfer_bysig_baddst) # Transfer to multisig address (l2,l3,l4)
    checkSuccessfulTransfer(tok, multisigs[0], multisigs[1], l1, xfernum, transfer_bysig_local2) # Transfer to multisig address (l2,l3,l4)



def test_simple_replay_transfer2of3(localaccounts, deploy_multisigs):
    a1, a2, a3 = accounts[1:4]
    l1, l2, l3, l4, l5 = localaccounts[0:5]
    
    tok, multisigs = deploy_multisigs

    checkSuccessfulTransfer(tok, a1, multisigs[0], a1, xfernum, transfer_direct) # Transfer *to* multisig address (l1,l2,l3)

    nonce, sig = generate_nonce_and_second_signature_transfer2of3(tok, l2.private_key, multisigs[0], a2, xfernum)


    def transfer_bysig_local2(tok: RUToken, src, dst, sender, amount):
        return transfer_bysig(tok, src, dst, sender, l2.private_key, amount)

    checkSuccessfulTransfer(tok, multisigs[0], a2, l1, xfernum, transfer_bysig_local2) # Transfer *to* multisig address (l1,l2,l3)
    with brownie.reverts():
        tx = tok.transfer2of3(multisigs[0], a2, xfernum, nonce, sig.encoded(), msg(l1))


def test_noncechange_replay_transfer2of3(localaccounts, deploy_multisigs):
    a1, a2, a3 = accounts[1:4]
    l1, l2, l3, l4, l5 = localaccounts[0:5]
    
    tok, multisigs = deploy_multisigs

    checkSuccessfulTransfer(tok, a1, multisigs[0], a1, xfernum * 3, transfer_direct) # Transfer *to* multisig address (l1,l2,l3)

    nonce, sig = generate_nonce_and_second_signature_transfer2of3(tok, l2.private_key, multisigs[0], a2, xfernum)


    def transfer_bysig_local2(tok: RUToken, src, dst, sender, amount):
        return transfer_bysig(tok, src, dst, sender, l2.private_key, amount)

    checkSuccessfulTransfer(tok, multisigs[0], a2, l1, xfernum, transfer_bysig_local2) # Transfer *to* multisig address (l1,l2,l3)
    
    nonce2, sig2 = generate_nonce_and_second_signature_transfer2of3(tok, l2.private_key, multisigs[0], a2, xfernum)

    with brownie.reverts():
        tx = tok.transfer2of3(multisigs[0], a2, xfernum, nonce2, sig.encoded(), msg(l1))



def test_multicontract_replay_transfer2of3(localaccounts, deploy_multisigs):
    a1, a2, a3 = accounts[1:4]
    l1, l2, l3, l4, l5 = localaccounts[0:5]
    
    tok, multisigs = deploy_multisigs

    tok2 = deploy_and_mint(price, maxtok, totalmint, a1)
    register_multisigs(tok2, localaccounts)

    checkSuccessfulTransfer(tok, a1, multisigs[0], a1, xfernum * 2, transfer_direct) # Transfer *to* multisig address (l1,l2,l3)
    checkSuccessfulTransfer(tok2, a1, multisigs[0], a1, xfernum * 2, transfer_direct) # Transfer *to* multisig address (l1,l2,l3)

    nonce, sig = generate_nonce_and_second_signature_transfer2of3(tok, l2.private_key, multisigs[0], a2, xfernum)

    def transfer_bysig_local2(tok: RUToken, src, dst, sender, amount):
        return transfer_bysig(tok, src, dst, sender, l2.private_key, amount)

    checkSuccessfulTransfer(tok, multisigs[0], a2, l1, xfernum, transfer_bysig_local2) # Transfer *to* multisig address (l1,l2,l3)

    with brownie.reverts():
        tx = tok2.transfer2of3(multisigs[0], a2, xfernum, nonce, sig.encoded(), msg(l1))

