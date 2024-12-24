import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QDialog,
    QFormLayout, QMessageBox
)
from PyQt5.QtCore import Qt

import numpy as np


class AddComponentDialog(QDialog):
    def __init__(self, node_count, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавление компонента")

        self.component_type = QComboBox()
        self.component_type.addItems(["Резистор", "Источник ЭДС"])

        self.node1_spin = QSpinBox()
        self.node2_spin = QSpinBox()
        self.node1_spin.setRange(0, node_count - 1)
        self.node2_spin.setRange(0, node_count - 1)

        self.value_edit = QLineEdit()

        form_layout = QFormLayout()
        form_layout.addRow("Тип компонента:", self.component_type)
        form_layout.addRow("Узел 1:", self.node1_spin)
        form_layout.addRow("Узел 2:", self.node2_spin)
        form_layout.addRow("Значение:", self.value_edit)

        self.ok_btn = QPushButton("Добавить")
        self.ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(cancel_btn)

        layout = QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def get_data(self):
        comp_type = "resistor" if self.component_type.currentText() == "Резистор" else "source"
        node1 = self.node1_spin.value()
        node2 = self.node2_spin.value()
        try:
            value = float(self.value_edit.text())
        except ValueError:
            value = 0.0
        return comp_type, node1, node2, value


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Расчет токов в электрической схеме")

        self.node_count = 3
        self.components = []

        main_widget = QWidget()
        main_layout = QVBoxLayout()

        node_layout = QHBoxLayout()
        node_label = QLabel("Количество узлов в схеме:")
        self.node_spin = QSpinBox()
        self.node_spin.setRange(2, 20)
        self.node_spin.setValue(self.node_count)
        node_layout.addWidget(node_label)
        node_layout.addWidget(self.node_spin)

        self.update_nodes_btn = QPushButton("Применить количество узлов")
        self.update_nodes_btn.clicked.connect(self.update_node_count)
        node_layout.addWidget(self.update_nodes_btn)

        main_layout.addLayout(node_layout)

        self.add_component_btn = QPushButton("Добавить компонент")
        self.add_component_btn.clicked.connect(self.add_component)
        main_layout.addWidget(self.add_component_btn)

        self.calc_btn = QPushButton("Рассчитать токи")
        self.calc_btn.clicked.connect(self.calculate_circuit)
        main_layout.addWidget(self.calc_btn)

        self.result_label = QLabel("")
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        main_layout.addWidget(self.result_label)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def update_node_count(self):
        self.node_count = self.node_spin.value()
        self.components.clear()
        self.result_label.setText("")
        QMessageBox.information(self, "Успех", f"Установлено {self.node_count} узлов. Список компонентов очищен.")

    def add_component(self):
        dialog = AddComponentDialog(self.node_count, self)
        if dialog.exec_() == QDialog.Accepted:
            comp_type, n1, n2, value = dialog.get_data()
            self.components.append((comp_type, n1, n2, value))
            QMessageBox.information(self, "Успех",
                                    f"Добавлен компонент: {comp_type}, узлы ({n1}, {n2}), значение {value}")

    def calculate_circuit(self):
        if len(self.components) == 0:
            self.result_label.setText("Нет компонентов для расчёта.")
            return

        n = self.node_count
        G = np.zeros((n, n), dtype=float)
        I = np.zeros(n, dtype=float)

        for comp_type, node1, node2, value in self.components:
            if comp_type == "resistor":
                if value == 0:
                    continue
                g = 1.0 / value
                G[node1, node1] += g
                G[node2, node2] += g
                G[node1, node2] -= g
                G[node2, node1] -= g

            elif comp_type == "source":
                G[node1, node1] += 1e9
                G[node1, node2] -= 1e9
                G[node2, node1] -= 1e9
                G[node2, node2] += 1e9
                I[node1] += 1e9 * value
                I[node2] -= 1e9 * value

        ref_node = n - 1
        mask = np.arange(n) != ref_node
        G_reduced = G[mask][:, mask]
        I_reduced = I[mask]

        try:
            V_solutions = np.linalg.solve(G_reduced, I_reduced)
        except np.linalg.LinAlgError:
            self.result_label.setText("Система не может быть решена (вырожденная матрица).")
            return

        V = np.zeros(n, dtype=float)
        idx = 0
        for i in range(n):
            if i != ref_node:
                V[i] = V_solutions[idx]
                idx += 1

        results = []
        for index, (comp_type, node1, node2, value) in enumerate(self.components):
            if comp_type == "resistor" and value != 0:
                current = (V[node1] - V[node2]) / value
                results.append(f"Компонент {index} (резистор): I = {current:.4f} А")
            elif comp_type == "source":
                current = 1e9 * (V[node1] - V[node2] - value)
                results.append(f"Компонент {index} (ЭДС): I = {current:.4e} А (упрощённо)")
            else:
                results.append(f"Компонент {index} (неизвестно): нет данных")

        msg = "Узловые потенциалы:\n"
        for i in range(n):
            msg += f"  V({i}) = {V[i]:.4f} В\n"
        msg += "\nТоки в компонентах:\n" + "\n".join(results)

        self.result_label.setText(msg)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
