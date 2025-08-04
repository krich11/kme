#!/bin/bash
# Multi-SAE Test Package Self-Extractor
# ETSI QKD 014 V1.1.1 Multi-SAE Testing Package

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Multi-SAE Test Package${NC}"
    echo -e "${BLUE}  ETSI QKD 014 V1.1.1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header

# Check for password
if [[ $# -eq 0 ]]; then
    read -s -p "Enter package password: " PASSWORD
    echo
else
    PASSWORD="$1"
fi

# Embedded encrypted data
ENCRYPTED_DATA="U2FsdGVkX185aiQPtEmYg1fNKzAeyuDAKyfVqQ8XIyfiYVJg1U0BNrqqG8431Fh1
WEkYvdtrdVAo74QY11PYDne3miv1lwHr3YJT6yoSpemKHqDoc0/ro+UMQqtlib8/
NJ/AW+g5JmSLsK2kTcu+675sf9Q6Y5eBgJKnEM5NmkhApgmhQKhsgIx28MFQm61a
WF6rq+Qek+cwEKLkrWhQB45WYI62FSLVAMt1oPKjW85K+IBR+93uwl1OaKS33HxD
DcAYuiwWxg6Pdh7XTDf96x7lBz3QmF8jKfyJn8onFrpv2t0rY64TJTEhPJJid1he
O7i6Spnk/0gEKDL1xhcuQw4L/nTvnPnEYNCF3G4tdmrU49hw5MDMi6w4aw6VNNPt
JVrh0OCurkH2jFCtGixuy7OdQ19pZgZk3BBk+jZkbm8AvM9qwiY6ri91sGuNPo/y
QZaM8gRnxTppGRrvAl0UkEkKqxqcN3SxliAe4l8LrBKtFX3PnIYXDsRhKrtSkq37
A++OZSJsO630JaQExhyMN1Z80rcGligLEh6nnFVReVHDzT18v6nXhkBcpLU3h4wG
ouitu1ilpFUPRvdK1yJC/1mWxoxuF81hEPD0ckiiQO48iw+UgOmtvenHqiRx3ekE
GcBOFgQeWCk5gqSwz+WnemgIC3544dklo/ItzIYwXZawxNPRTAmbMUSS8+PcJxOQ
zlBzn8xqiK59NrFOBogA0BxQ33ukG32v7NVW5kRgAojSIFWkOOY87e6eKS1p0y7m
JahAVWl+yfpi/4b8b9VHInUOYLLB9dXMtpEiz/mlJVWWsOIsUmuKQP5zuv54Zp/m
jXMmRNQH5DlvDshjVbc2OMnmA8cC7SOnlEe8Si2fkZO577Leg35M9ySNJPPJUTfM
bc4v5/JYFVkH/6nHJH6PtBXPnd+eZe6+GCVoukbJdX1YCkRaUOk/osIVS8zcAESR
/hF7LxluMc8zLTvd846s+aseVVeilAIjBawnbN7tVAUyS+iOvPaS+Lzcr2seS+sq
kdL7WNUM6PQfNCdGhBMlhk6ArIXLAGDw2cYC80Ouxu38rk4TzcPUtAZQcfjT8niO
+2QorihumrCcXLCX9DGFH6b5+ODHi3cATzaFzNWNsdwhMP3c4mviWoR0NY3x8vRa
uL08lQM8sP6k8XoCE7zTFitZyRvBUU8JMjuHSdxwTo/iYn76dDL4eelt+Bns89Sy
iFD3I47VHdsyXvilhw1I9ecRRjdehR9CJgoG6KRMrpSq1MYuWMUzUw/4DWquikaN
/9xRpZDvO793UE5B527Koq5yluEjbqj8X0UiojeN1JmZlroWImOzaLLBEJKZWiaS
baJl+CTLi15/w2PucicRZhQgje0h2iIZ/CauMzcXh5mzDzs08fHBHsGEZFE5k7R8
e++b10kwm6rtf+M+Vtg9XbxDQJsdRGN3f8dOXKYp4K8Xzj9Po4iNDhEgbmwyqVrU
4zvIV2bSPIolfe01a2LOdoFw9r7Idr5Q/FWigAvfiK7zFN+hTe8Heq1TsIFyn+Od
V8EhItE9dDc9WLfp0g7rbvFZJoht2YqBZFMI+8F5E5E/kOMpLkbWvtojCtlx9s2J
w+2f4fAQRovfGa37D/1oBdenRuukt7nNWRD0+wbOqksiORwO8/5pZdqGyyNLZ/jW
/ZUBqpAzZbe5e2O51XgOnxpw0h7HGdWL/8e692SGGE9TooIFxyDIbun6SEtjZTkB
qBEmyU+vrhD2rM1yPbmyRIfZKIH0y2t+duiOgJsqVFQLShJioRuiAyx820BkBlq8
vJ7xbOXZwhBV01qjKtqHwh/heLhvk9tDYfe941ZuPQLmMo27EuUiRbapAVqWWzL8
lDqWvKJn11+MiAUuGP+D8KKhaCQDaPj15Q+DLle50dXffV9gFo2NUUqIMk4X5xLt
9Fyb2FjsgSQUdzLOtJMt8QK5Yv1EmQdVf/4YNK3jgdIwjSbsFJNffe1HZE8SH2zc
+dX35zJ6OgCMp3JQqXk3E4zEAUtz1sHG/VumqOmYj+Qw5ztNqYwiyWlz5OFCik27
d+VN3h6t2wT0KLm0Nd8J+jO1k+avKogVXqSGxh4w+/z1J1GHvEnd8GEP6SeuGvSk
KLRWDxEcNqJTUdD7rn5hTjW97zmtNQ4z7aD9cqR6RZUBfGL3aFuewTbzYsBc1HYP
8Bw89QPGodylmpE8EakW5Qow0VwsZ1kbDsVbkWJSklPKjRvkWH86XMBAsKDb9GPh
Jp2sJ2dgf+AULw8riymQcN/Njc3Av4vUoR5qLjIPiOUeXcia7JvFK+5HGTdfmAmN
QeagRpcYkc9B9X6itSKNgIyRfhRDl226oUx24XnMWAZpN3Kat0thNtq3KpUK3lpa
dkdbO/EDpI27fySUH4UtWQkrAmNmrN6Xn2mcGPEo2bJ8cIZewA14i5WvBEZWBF7g
fAaijrKGRNhZPBCcwVlb3FG9AaRD2lyOkIvPIUiNBePt5tvIbN/0UuYkoQcXY2pf
6f/8A4328KyLo6xrVy0+zHKT4xR2DeuF4ECo6/F1439bl63n+kNOtrB7yQiv2cBA
GkTDRjENmInWa0253rUe/K4l18pU9S44AmAFa+uEa7825JdfnbOCT/PQLuQrKk23
ZfK64E9zy29ckTWDDvEyrKIvlGI8rvAQF1a9axHCZx00kail4guzIZJb+daNz6Gx
RlDZKJhsl70sFJYmjAMDgIsAHE53Hekync9g8JZ2hK9FN32ROM8L4TPsquIL8Lxk
H7GbQR98nbSoISsuj5xNH+MJyc2kCrAiJeEdFoH1jIXswQsUYaaCvdT4ayXHvAFY
jYacaok7uSeVCilQVo2UflwjB8quUmD0AOFhf+T/CFkfLITvVKO3iSHPOeJqXJlL
h/NdzwYkbDEW62S5NiR43tPtR7xYfbKH90Ho80a2K1PXlmfWPAgR1DDTtDw1QtNO
/D7+KO97s27HII9xM7RykUgU2uTXC8qP5dgOHDyz+SBgilJwCOzsiEpkGaKF7n4L
bb5kQeqC8cHv2Mnj0UR7EOuL/unmj44DKUnIAJopSG1AbJ46m4xVhHoS3vDvSC6L
jbh4Bd24HOJlTlw+bC7HtCbF2Ygi+fepjxeda9hI3VPCYIbv5NMgiysoo62en7CF
85rItWq5PZtqYTyxGz9Lt36xAi/Q83nrI2D0QvmwyEgX/vvXkWMgKd6j31iMRScy
MP9bvy+ObhsyoT9htJ0HIEMsfu+6TATkCZmL9+79s6BjLEy/nFlt+16lzQ7VAUDX
Yz+3G6NctOuwr500dW/yEzGqnMt3nFsWzSKZC5apPyR8y/s+pXYXn8Qf4T4faNEZ
IoTkPqeX+JJYmXBz0dbyMgn3YL8IVGKMHAUtnPaq128fdbvODi0AhG9YJqLKbQ0u
qIXhpngnyiOJcMsm9300glduCeMZG4ixbvA45wnfVOguV/Gn0II8cIjXBbjdSquO
hiJqtn71t70efJ2eiT1h+rwzNyRCjpbnQt9rxm8MtAEdeSiBYtB5ZwaOjDzxJzie
kSJteSYn26tNk4XeJBsqfXRcldWy1aeIoNu7MhVlV2/3c/qq6V8oYYouyxATERcG
dO3loBi6JsnSH7Ak/WcYV8DkQlMt4/p+gQZZsBa9BeT5AjOfTWO0cQvQ7tYMhcV2
jLipeIjBCTDDQhdHqy4ib2gqSWp7CCizDUjgHC68l/zpU12JaeM24so1ksf2V6eq
+s1CDVBFZsT8UKCJ3oFTQEr/lFxaT/0cksEMoKFhfZ0gT7Y4NCP4KIZUXXETi9P7
+y7UkzvQXbLtuzXWid973UAzCMdFB8UvaQxcPwKlUE2RbuQUEVPOmW5QuvEkEsIF
ja6W2ZJ6LGhIPEf4ZVQkDhwrAvpslH3f0yyBeei97XQu41YXcLFmyNW/F0ynCmFa
0GVAjvrdxSzIOPrmXsNPy3esYAnTDHQdywU7dE5GwhdueNSWdxmZnW3kVhoFwYyk
5eA4TLWbjCAtfcYdGeEVP6ISvxX1u/WBt4iZVpIrxO40Gy4lm8ATNCC1+/FPet7w
HNJ2Ec9eSrKeo85836Kb71YHkNTQQkmk+qpL5D/wcmdhUkiSP2RXE/fGqM5ntDH8
PnGe9VS3EWPU02cayIAzTJiqIDlG5ovOvS4aJVsChsvpvdGUKNZzmuJpSHyNWUTL
Qu+VsuO80lCcQ79O+7M3X5WbGEchsbhB/blgCUrl8pt1wQ5JfEQaiWev7/0tolGc
rSQFYmxVWNk3DmQJJyM04nc9WUnBp8GI8VaYxaVEYj9BhVg8+SPEsUIFiohpV++8
WcKKQ3d4jD3K6JaANvE8tucFU/wNzb2uew/uuPmEQBX4SMR7fXO7ZXeMauEBIUD9
AJwgowUR3/N9szWh2hcXXkvOXkepF/3vaHLgzoZ/kw81xs7f1m0KqrNr2EGM27Zf
+3l1HFkK4oIrME4l9xw+8CuS83M96yR/sM0+AXn/Y7u57Qp2KeEL8GHrgG8VwMYL
vNc0roy3AiMcCpWOI41msLh3jX+batF9T5OI0BYjq0atL3XJPknRn69tSLNGauaO
of/yWHijT+dYQo8tRb1xWq5zphLO1Ojj8kskiBU81GNFEwjrLDDE5nb21/T0TMaN
jE+/zJfW9aTD3tgzydlbiZV9JVz8aXqJGQ8h+BfS1NLlgV+A4ZDcjYtPwlNq5whM
m4N6G90bNb5e3qwtsH4W9WqeOc39hgATp47DRPoTBQtDJfmQNv6m4ITAv/8g8+HH
cNcUk88z/Ux7PcXKMYoAdujBdYVlU8gwb2SToXqPpQikorur+aKnzBTupPhLvUmo
UYD3mu7BOVnqmKlHl99CQV7haB/MT1Jc+riJefd/vJa7nOFsagueXHwtQIDfH78t
69XYq9G/7WFbKvcAUlKuTW4ZAHUeLWFJdj0BG7gkTXCyr1yvJ8iIcuaPDMkPAan4
NwKAkoZR1VE+k3VCbu65N+e1CoETejgMiMDpS6JjxvlkIlslt+WGe9fbGNjpTdxu
QhG/qBSxOqS4sf6xyR0+cVUfawm1vbnzsbTTQZTL9KGAYVdFJg9IaavOzw7DT1oP
Qum6eolhcv1fTJ1ujzOwYvW+7VSqyfD+iODomdVBjzQWWnQU9K+ZhnhdY8AspBI0
H7ua+VnBQ18octDBabj37QREn3r9kffvd5d5MSgrhp/i1QmtjVcQ73kKj/u0lg7N
QcapWGslQZjPjpTyShwpdAdBIpG4Iio0H3FzXaOAPg9Qz0sPDUgr0Vp3FSgoTxJU
Qka8O/WzTuR7pu3ACClvaA3jtJEB6YEFqCcoyS9Rr98="

# Create extraction directory
EXTRACT_DIR="multi_sae_test_package"
mkdir -p "$EXTRACT_DIR"
cd "$EXTRACT_DIR"

print_status "Extracting package contents..."

# Decrypt and extract
if ! echo "$ENCRYPTED_DATA" |     openssl enc -aes-256-cbc -d -salt -pbkdf2         -pass "pass:$PASSWORD"         -a         -out "package.tar.gz" 2>/dev/null; then
    print_error "Invalid password or corrupted package"
    rm -f "package.tar.gz"
    exit 1
fi

# Extract package contents
if ! tar -xzf package.tar.gz; then
    print_error "Failed to extract package contents"
    exit 1
fi

# Remove temporary archive
rm package.tar.gz

print_status "Package extracted successfully!"
print_status "Directory: $EXTRACT_DIR"

echo ""
echo "Next steps:"
echo "1. cd $EXTRACT_DIR"
echo "2. ./multi_sae_test.sh"
echo ""
echo "This will run the comprehensive multi-SAE test suite."
