// 주기율표 데이터 (1-6주기)
const elements = [
    // 1주기
    { number: 1, symbol: 'H', name: 'Hydrogen', mass: 1.008, row: 1, col: 1 },
    { number: 2, symbol: 'He', name: 'Helium', mass: 4.003, row: 1, col: 18 },

    // 2주기
    { number: 3, symbol: 'Li', name: 'Lithium', mass: 6.941, row: 2, col: 1 },
    { number: 4, symbol: 'Be', name: 'Beryllium', mass: 9.012, row: 2, col: 2 },
    { number: 5, symbol: 'B', name: 'Boron', mass: 10.81, row: 2, col: 13 },
    { number: 6, symbol: 'C', name: 'Carbon', mass: 12.01, row: 2, col: 14 },
    { number: 7, symbol: 'N', name: 'Nitrogen', mass: 14.01, row: 2, col: 15 },
    { number: 8, symbol: 'O', name: 'Oxygen', mass: 16.00, row: 2, col: 16 },
    { number: 9, symbol: 'F', name: 'Fluorine', mass: 19.00, row: 2, col: 17 },
    { number: 10, symbol: 'Ne', name: 'Neon', mass: 20.18, row: 2, col: 18 },

    // 3주기
    { number: 11, symbol: 'Na', name: 'Sodium', mass: 22.99, row: 3, col: 1 },
    { number: 12, symbol: 'Mg', name: 'Magnesium', mass: 24.31, row: 3, col: 2 },
    { number: 13, symbol: 'Al', name: 'Aluminum', mass: 26.98, row: 3, col: 13 },
    { number: 14, symbol: 'Si', name: 'Silicon', mass: 28.09, row: 3, col: 14 },
    { number: 15, symbol: 'P', name: 'Phosphorus', mass: 30.97, row: 3, col: 15 },
    { number: 16, symbol: 'S', name: 'Sulfur', mass: 32.07, row: 3, col: 16 },
    { number: 17, symbol: 'Cl', name: 'Chlorine', mass: 35.45, row: 3, col: 17 },
    { number: 18, symbol: 'Ar', name: 'Argon', mass: 39.95, row: 3, col: 18 },

    // 4주기
    { number: 19, symbol: 'K', name: 'Potassium', mass: 39.10, row: 4, col: 1 },
    { number: 20, symbol: 'Ca', name: 'Calcium', mass: 40.08, row: 4, col: 2 },
    { number: 21, symbol: 'Sc', name: 'Scandium', mass: 44.96, row: 4, col: 3 },
    { number: 22, symbol: 'Ti', name: 'Titanium', mass: 47.87, row: 4, col: 4 },
    { number: 23, symbol: 'V', name: 'Vanadium', mass: 50.94, row: 4, col: 5 },
    { number: 24, symbol: 'Cr', name: 'Chromium', mass: 52.00, row: 4, col: 6 },
    { number: 25, symbol: 'Mn', name: 'Manganese', mass: 54.94, row: 4, col: 7 },
    { number: 26, symbol: 'Fe', name: 'Iron', mass: 55.85, row: 4, col: 8 },
    { number: 27, symbol: 'Co', name: 'Cobalt', mass: 58.93, row: 4, col: 9 },
    { number: 28, symbol: 'Ni', name: 'Nickel', mass: 58.69, row: 4, col: 10 },
    { number: 29, symbol: 'Cu', name: 'Copper', mass: 63.55, row: 4, col: 11 },
    { number: 30, symbol: 'Zn', name: 'Zinc', mass: 65.38, row: 4, col: 12 },
    { number: 31, symbol: 'Ga', name: 'Gallium', mass: 69.72, row: 4, col: 13 },
    { number: 32, symbol: 'Ge', name: 'Germanium', mass: 72.63, row: 4, col: 14 },
    { number: 33, symbol: 'As', name: 'Arsenic', mass: 74.92, row: 4, col: 15 },
    { number: 34, symbol: 'Se', name: 'Selenium', mass: 78.97, row: 4, col: 16 },
    { number: 35, symbol: 'Br', name: 'Bromine', mass: 79.90, row: 4, col: 17 },
    { number: 36, symbol: 'Kr', name: 'Krypton', mass: 83.80, row: 4, col: 18 },

    // 5주기
    { number: 37, symbol: 'Rb', name: 'Rubidium', mass: 85.47, row: 5, col: 1 },
    { number: 38, symbol: 'Sr', name: 'Strontium', mass: 87.62, row: 5, col: 2 },
    { number: 39, symbol: 'Y', name: 'Yttrium', mass: 88.91, row: 5, col: 3 },
    { number: 40, symbol: 'Zr', name: 'Zirconium', mass: 91.22, row: 5, col: 4 },
    { number: 41, symbol: 'Nb', name: 'Niobium', mass: 92.91, row: 5, col: 5 },
    { number: 42, symbol: 'Mo', name: 'Molybdenum', mass: 95.95, row: 5, col: 6 },
    { number: 43, symbol: 'Tc', name: 'Technetium', mass: 98.00, row: 5, col: 7 },
    { number: 44, symbol: 'Ru', name: 'Ruthenium', mass: 101.1, row: 5, col: 8 },
    { number: 45, symbol: 'Rh', name: 'Rhodium', mass: 102.9, row: 5, col: 9 },
    { number: 46, symbol: 'Pd', name: 'Palladium', mass: 106.4, row: 5, col: 10 },
    { number: 47, symbol: 'Ag', name: 'Silver', mass: 107.9, row: 5, col: 11 },
    { number: 48, symbol: 'Cd', name: 'Cadmium', mass: 112.4, row: 5, col: 12 },
    { number: 49, symbol: 'In', name: 'Indium', mass: 114.8, row: 5, col: 13 },
    { number: 50, symbol: 'Sn', name: 'Tin', mass: 118.7, row: 5, col: 14 },
    { number: 51, symbol: 'Sb', name: 'Antimony', mass: 121.8, row: 5, col: 15 },
    { number: 52, symbol: 'Te', name: 'Tellurium', mass: 127.6, row: 5, col: 16 },
    { number: 53, symbol: 'I', name: 'Iodine', mass: 126.9, row: 5, col: 17 },
    { number: 54, symbol: 'Xe', name: 'Xenon', mass: 131.3, row: 5, col: 18 },

    // 6주기
    { number: 55, symbol: 'Cs', name: 'Cesium', mass: 132.9, row: 6, col: 1 },
    { number: 56, symbol: 'Ba', name: 'Barium', mass: 137.3, row: 6, col: 2 },
    { number: 57, symbol: 'La', name: 'Lanthanum', mass: 138.9, row: 6, col: 3 },
    { number: 58, symbol: 'Ce', name: 'Cerium', mass: 140.1, row: 6, col: 3 },
    { number: 59, symbol: 'Pr', name: 'Praseodymium', mass: 140.9, row: 6, col: 3 },
    { number: 60, symbol: 'Nd', name: 'Neodymium', mass: 144.2, row: 6, col: 3 },
    { number: 61, symbol: 'Pm', name: 'Promethium', mass: 145.0, row: 6, col: 3 },
    { number: 62, symbol: 'Sm', name: 'Samarium', mass: 150.4, row: 6, col: 3 },
    { number: 63, symbol: 'Eu', name: 'Europium', mass: 152.0, row: 6, col: 3 },
    { number: 64, symbol: 'Gd', name: 'Gadolinium', mass: 157.3, row: 6, col: 3 },
    { number: 65, symbol: 'Tb', name: 'Terbium', mass: 158.9, row: 6, col: 3 },
    { number: 66, symbol: 'Dy', name: 'Dysprosium', mass: 162.5, row: 6, col: 3 },
    { number: 67, symbol: 'Ho', name: 'Holmium', mass: 164.9, row: 6, col: 3 },
    { number: 68, symbol: 'Er', name: 'Erbium', mass: 167.3, row: 6, col: 3 },
    { number: 69, symbol: 'Tm', name: 'Thulium', mass: 168.9, row: 6, col: 3 },
    { number: 70, symbol: 'Yb', name: 'Ytterbium', mass: 173.1, row: 6, col: 3 },
    { number: 71, symbol: 'Lu', name: 'Lutetium', mass: 175.0, row: 6, col: 3 },
    { number: 72, symbol: 'Hf', name: 'Hafnium', mass: 178.5, row: 6, col: 4 },
    { number: 73, symbol: 'Ta', name: 'Tantalum', mass: 180.9, row: 6, col: 5 },
    { number: 74, symbol: 'W', name: 'Tungsten', mass: 183.8, row: 6, col: 6 },
    { number: 75, symbol: 'Re', name: 'Rhenium', mass: 186.2, row: 6, col: 7 },
    { number: 76, symbol: 'Os', name: 'Osmium', mass: 190.2, row: 6, col: 8 },
    { number: 77, symbol: 'Ir', name: 'Iridium', mass: 192.2, row: 6, col: 9 },
    { number: 78, symbol: 'Pt', name: 'Platinum', mass: 195.1, row: 6, col: 10 },
    { number: 79, symbol: 'Au', name: 'Gold', mass: 197.0, row: 6, col: 11 },
    { number: 80, symbol: 'Hg', name: 'Mercury', mass: 200.6, row: 6, col: 12 },
    { number: 81, symbol: 'Tl', name: 'Thallium', mass: 204.4, row: 6, col: 13 },
    { number: 82, symbol: 'Pb', name: 'Lead', mass: 207.2, row: 6, col: 14 },
    { number: 83, symbol: 'Bi', name: 'Bismuth', mass: 209.0, row: 6, col: 15 },
    { number: 84, symbol: 'Po', name: 'Polonium', mass: 209.0, row: 6, col: 16 },
    { number: 85, symbol: 'At', name: 'Astatine', mass: 210.0, row: 6, col: 17 },
    { number: 86, symbol: 'Rn', name: 'Radon', mass: 222.0, row: 6, col: 18 }
];

// 선택된 원소들
let selectedElements = new Set();

// 주기율표 렌더링
function renderPeriodicTable() {
    const table = document.getElementById('periodicTable');
    table.innerHTML = '';

    // 6행 18열 그리드 생성
    for (let row = 1; row <= 6; row++) {
        for (let col = 1; col <= 18; col++) {
            const element = elements.find(e => e.row === row && e.col === col);

            if (element) {
                const div = document.createElement('div');
                div.className = 'element';
                div.dataset.symbol = element.symbol;
                div.style.gridRow = row;
                div.style.gridColumn = col;

                div.innerHTML = `
                    <div class="element-number">${element.number}</div>
                    <div class="element-symbol">${element.symbol}</div>
                    <div class="element-mass">${element.mass}</div>
                `;

                div.addEventListener('click', () => toggleElement(element.symbol));
                table.appendChild(div);
            } else {
                const spacer = document.createElement('div');
                spacer.className = 'spacer';
                spacer.style.gridRow = row;
                spacer.style.gridColumn = col;
                table.appendChild(spacer);
            }
        }
    }
}

// 원소 선택/해제
function toggleElement(symbol) {
    const elementDiv = document.querySelector(`.element[data-symbol="${symbol}"]`);

    if (selectedElements.has(symbol)) {
        selectedElements.delete(symbol);
        elementDiv.classList.remove('selected');
    } else {
        selectedElements.add(symbol);
        elementDiv.classList.add('selected');
    }

    renderInputFields();
}

// 입력 필드 렌더링
function renderInputFields() {
    const container = document.getElementById('elementInputs');
    container.innerHTML = '';

    if (selectedElements.size === 0) {
        container.innerHTML = '<p style="text-align: center; color: #999;">주기율표에서 원소를 선택하세요.</p>';
        return;
    }

    selectedElements.forEach(symbol => {
        const element = elements.find(e => e.symbol === symbol);

        const div = document.createElement('div');
        div.className = 'element-input-row';
        div.innerHTML = `
            <div class="element-input-header">
                <span class="element-name">${element.symbol} (${element.name})</span>
                <label class="bal-checkbox">
                    <input type="checkbox" id="bal-${symbol}" onchange="handleBalChange('${symbol}')">
                    <span>bal.</span>
                </label>
            </div>
            <div class="input-fields">
                <div class="input-field">
                    <label>at%</label>
                    <input type="number" id="at-${symbol}" step="0.01" min="0" max="100"
                           oninput="handleInput('${symbol}', 'at')">
                </div>
                <div class="input-field">
                    <label>wt%</label>
                    <input type="number" id="wt-${symbol}" step="0.01" min="0" max="100"
                           oninput="handleInput('${symbol}', 'wt')">
                </div>
            </div>
        `;

        container.appendChild(div);
    });
}

// bal. 체크박스 처리
function handleBalChange(symbol) {
    const balCheckbox = document.getElementById(`bal-${symbol}`);
    const atInput = document.getElementById(`at-${symbol}`);
    const wtInput = document.getElementById(`wt-${symbol}`);

    if (balCheckbox.checked) {
        atInput.disabled = true;
        wtInput.disabled = true;
        atInput.value = '';
        wtInput.value = '';
    } else {
        atInput.disabled = false;
        wtInput.disabled = false;
    }
}

// 입력 처리 (한쪽 입력하면 다른쪽 비우기)
function handleInput(symbol, type) {
    const atInput = document.getElementById(`at-${symbol}`);
    const wtInput = document.getElementById(`wt-${symbol}`);

    if (type === 'at' && atInput.value) {
        wtInput.value = '';
    } else if (type === 'wt' && wtInput.value) {
        atInput.value = '';
    }
}

// 계산 버튼
function calculate() {
    const warnings = document.getElementById('warnings');
    warnings.innerHTML = '';
    warnings.className = 'warnings';

    // 입력 데이터 수집
    const inputData = [];
    let balElement = null;
    let hasAtInput = false;
    let hasWtInput = false;

    selectedElements.forEach(symbol => {
        const balCheckbox = document.getElementById(`bal-${symbol}`);
        const atInput = document.getElementById(`at-${symbol}`);
        const wtInput = document.getElementById(`wt-${symbol}`);
        const element = elements.find(e => e.symbol === symbol);

        if (balCheckbox.checked) {
            balElement = { symbol, element };
        } else {
            const atValue = parseFloat(atInput.value);
            const wtValue = parseFloat(wtInput.value);

            if (!isNaN(atValue)) {
                hasAtInput = true;
                inputData.push({ symbol, element, at: atValue, wt: null });
            } else if (!isNaN(wtValue)) {
                hasWtInput = true;
                inputData.push({ symbol, element, at: null, wt: wtValue });
            }
        }
    });

    // 입력 검증
    if (inputData.length === 0 && !balElement) {
        showWarning('error', '최소 하나의 원소에 값을 입력해주세요.');
        return;
    }

    if (hasAtInput && hasWtInput) {
        showWarning('error', 'at%와 wt%를 혼합하여 입력할 수 없습니다. 하나의 단위만 사용해주세요.');
        return;
    }

    // at% → wt% 변환
    if (hasAtInput) {
        convertAtToWt(inputData, balElement);
    }
    // wt% → at% 변환
    else if (hasWtInput) {
        convertWtToAt(inputData, balElement);
    }
}

// at% → wt% 변환
function convertAtToWt(inputData, balElement) {
    const warnings = document.getElementById('warnings');

    // bal. 원소가 있으면 계산
    if (balElement) {
        const totalAt = inputData.reduce((sum, d) => sum + d.at, 0);
        const balAt = 100 - totalAt;

        if (balAt < 0) {
            showWarning('error', `입력한 at%의 합이 100%를 초과했습니다 (${totalAt.toFixed(2)}%).`);
            return;
        }

        inputData.push({
            symbol: balElement.symbol,
            element: balElement.element,
            at: balAt,
            wt: null
        });
    }

    // at% 합계 검증
    const totalAt = inputData.reduce((sum, d) => sum + d.at, 0);

    // wt% 계산
    const denominator = inputData.reduce((sum, d) => sum + (d.at * d.element.mass), 0);

    inputData.forEach(data => {
        data.wt = (data.at * data.element.mass / denominator) * 100;

        // 결과 표시
        const wtInput = document.getElementById(`wt-${data.symbol}`);
        wtInput.value = data.wt.toFixed(2);

        // bal. 원소면 at% 값도 표시
        if (data.symbol === balElement?.symbol) {
            const atInput = document.getElementById(`at-${data.symbol}`);
            atInput.value = data.at.toFixed(2);
        }
    });

    // 합계 검증 및 경고
    const totalWt = inputData.reduce((sum, d) => sum + d.wt, 0);

    if (Math.abs(totalAt - 100) > 0.01) {
        showWarning('warning', `at% 합계: ${totalAt.toFixed(2)}% (100%가 아닙니다)`);
    } else if (Math.abs(totalWt - 100) > 0.01) {
        showWarning('warning', `wt% 합계: ${totalWt.toFixed(2)}% (계산 오차)`);
    } else {
        showWarning('success', `✓ 변환 완료 (at% → wt%)`);
    }
}

// wt% → at% 변환
function convertWtToAt(inputData, balElement) {
    const warnings = document.getElementById('warnings');

    // bal. 원소가 있으면 계산
    if (balElement) {
        const totalWt = inputData.reduce((sum, d) => sum + d.wt, 0);
        const balWt = 100 - totalWt;

        if (balWt < 0) {
            showWarning('error', `입력한 wt%의 합이 100%를 초과했습니다 (${totalWt.toFixed(2)}%).`);
            return;
        }

        inputData.push({
            symbol: balElement.symbol,
            element: balElement.element,
            at: null,
            wt: balWt
        });
    }

    // wt% 합계 검증
    const totalWt = inputData.reduce((sum, d) => sum + d.wt, 0);

    // at% 계산
    const denominator = inputData.reduce((sum, d) => sum + (d.wt / d.element.mass), 0);

    inputData.forEach(data => {
        data.at = (data.wt / data.element.mass / denominator) * 100;

        // 결과 표시
        const atInput = document.getElementById(`at-${data.symbol}`);
        atInput.value = data.at.toFixed(2);

        // bal. 원소면 wt% 값도 표시
        if (data.symbol === balElement?.symbol) {
            const wtInput = document.getElementById(`wt-${data.symbol}`);
            wtInput.value = data.wt.toFixed(2);
        }
    });

    // 합계 검증 및 경고
    const totalAt = inputData.reduce((sum, d) => sum + d.at, 0);

    if (Math.abs(totalWt - 100) > 0.01) {
        showWarning('warning', `wt% 합계: ${totalWt.toFixed(2)}% (100%가 아닙니다)`);
    } else if (Math.abs(totalAt - 100) > 0.01) {
        showWarning('warning', `at% 합계: ${totalAt.toFixed(2)}% (계산 오차)`);
    } else {
        showWarning('success', `✓ 변환 완료 (wt% → at%)`);
    }
}

// 경고 표시
function showWarning(type, message) {
    const warnings = document.getElementById('warnings');
    warnings.className = `warnings ${type}`;
    warnings.innerHTML = message;
}

// 초기화
function reset() {
    selectedElements.forEach(symbol => {
        const elementDiv = document.querySelector(`.element[data-symbol="${symbol}"]`);
        elementDiv.classList.remove('selected');
    });

    selectedElements.clear();
    renderInputFields();

    const warnings = document.getElementById('warnings');
    warnings.innerHTML = '';
    warnings.className = 'warnings';
}

// 이벤트 리스너
document.getElementById('calculateBtn').addEventListener('click', calculate);
document.getElementById('resetBtn').addEventListener('click', reset);

// 초기화
renderPeriodicTable();
renderInputFields();
