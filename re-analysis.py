#!/usr/bin/env python
# coding: utf-8

# # 1. EDA

# In[49]:


import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import japanize_matplotlib
import seaborn as sns
from ydata_profiling import ProfileReport
from scipy import stats
from scipy import special

pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)

df_train = pd.read_csv("train_test_submission/train.csv")
df_train_Id = df_train["Id"]
df_train = df_train.drop("Id", axis=1)

df_test = pd.read_csv("train_test_submission/test.csv")
df_test_Id = df_test["Id"]
df_test = df_test.drop("Id", axis=1)

df_all_data = pd.concat([df_train, df_test])

print(f"df_train.shape: {df_train.shape}")
display(df_train.head(5))
print(f"df_train.shape: {df_test.shape}")
display(df_test.head(5))

print("-" * 10, "df_train.info()", "-" * 10)
print(df_train.info())
print("\n", "-" * 10, "df_test.info()", "-" * 10)
print(df_test.info())



# # ydata_profilingを使う場合。時間かかるので注意

# if not os.path.exists("ydata_profiling"):
#     os.makedirs("ydata_profiling")

# profile = ProfileReport(df_all_data, minimal=True)
# profile.to_file("ydata_profiling/kaggle_houseprices_minimal.html")

# # profile = ProfileReport(df_all_data, minimal=False)
# # profile.to_file("ydata_profiling/kaggle_houseprices.html")


# In[41]:


print("-" * 10, "df_train.columns", "-" * 10)
print(df_train.columns)


# In[42]:


print("-" * 10, 'df_train["SalePrice"].describe()', "-" * 10)
print(df_train["SalePrice"].describe())

# SalePriceの分布
sns.histplot(df_train["SalePrice"], kde=True)
plt.suptitle("目的変数SalePriceの分布")
plt.show()


# In[43]:


corr_matrix = df_train.corr(numeric_only=True)
"""
    訓練データdf_trainの相関係数行列
    corr_matrix = df_train.corr(numeric_only=True)
"""

plt.figure(figsize=(12, 10))
sns.heatmap(abs(corr_matrix), annot=True, fmt=".1f", annot_kws={"fontsize": 6})

plt.suptitle("訓練データの相関係数(絶対値)行列_カテゴリ変数を除く")
plt.show()


# In[44]:


# plotly版。インデックス番号が一目で確認できる

import plotly.express as px
import plotly.subplots as sp

threshold = 0.6
high_corr_cols = (
    corr_matrix["SalePrice"][abs(corr_matrix["SalePrice"]) >= threshold]
    .sort_values(ascending=False)
    .index
).drop("SalePrice")

# プロットのサイズを指定
num_cols = len(high_corr_cols)
rows = num_cols // 3 + 1  # 行数
cols = 3  # 列数

# サブプロットの作成
fig = sp.make_subplots(
    rows=rows, 
    cols=cols, 
    subplot_titles=[f"{col} vs SalePrice （相関係数{corr_matrix["SalePrice"][col]:.3f}）" for col in high_corr_cols],
    horizontal_spacing=0.05,
    vertical_spacing=0.1,
    )

# high_corr_colsにある特徴量ごとに散布図を描く
for i, col in enumerate(high_corr_cols):
    row = i // cols + 1
    col_num = i % cols + 1
    scatter = px.scatter(df_train, x=col, y="SalePrice", opacity=0.3, hover_data=[df_train.index])
    for trace in scatter.data:
        fig.add_trace(trace, row=row, col=col_num)
    fig.update_annotations()

# グラフのタイトルを設定
fig.update_layout(
    title_text=f"SalePriceとの相関係数の絶対値が{threshold}以上の特徴量についての散布図",
    showlegend=False,
    height=400 * rows,
    width=1200,
)

# グラフの表示
fig.show()

# レイアウト調節 https://data-analytics.fun/2021/06/19/plotly-subplots/


# # 2. 前処理

# In[45]:


# 外れ値処理(訓練データ)
df_train_befdrop = df_train
df_train = df_train.drop(df_train.index[[523, 1298]])

fig = px.scatter(df_train, x="GrLivArea", y="SalePrice", opacity=0.3, hover_data=[df_train.index])

fig.update_layout(
    title_text='x="GrLivArea", y="SalePrice"',
    showlegend=False,
    height=600,
    width=700,
)

# グラフの表示
fig.show()


# In[46]:


# 欠損値処理(訓練データ、テストデータ)
df_all_data = pd.concat([df_train, df_test])

df_missing_values_count = df_all_data.isna().sum()
df_missing_values_table = pd.DataFrame(
    {
        "Missing_count": df_missing_values_count,
        "Percent (%)": round(df_missing_values_count / len(df_all_data) * 100, 2)
    }
).sort_values("Missing_count", ascending=False)

# chatGPTに作ってもらった各特徴量の説明をまとめたcsvを読み込む
df_data_description = pd.read_csv(
    "data_description/data_descripsion_simple_jp.csv", index_col=0
)
# 各特徴量の欠損値に関する表と、各特徴量の説明に関する表を結合
df_missing_value_description = pd.concat([df_missing_values_table, df_data_description], axis=1)
# csvに出力。これとydata_profilingのレポートを眺めながら各欠損値をどう処理するか考える。
if not os.path.exists("missing_value"):
    os.makedirs("missing_value")
df_missing_value_description.to_csv(
    "missing_value/missing_value_processing.csv", encoding="utf-8_sig"
)

display(df_missing_value_description.head(40))


# In[37]:


# 特徴量エンジニアリング(訓練データ、テストデータ)
# 新しい特徴量の作成
# 'YrBltAndRemod': 'YearBuilt' + 'YearRemodAdd'

datasets = [df_train, df_test]
for i in range(len(datasets)):
    datasets[i]["TotalSF"] = (
        datasets[i]["TotalBsmtSF"]
        + datasets[i]["1stFlrSF"] 
        + datasets[i]["2ndFlrSF"]
    )
    datasets[i]["TotalFinSF"] = (
        datasets[i]["BsmtFinSF1"]
        + datasets[i]["BsmtFinSF2"]
        + datasets[i]["1stFlrSF"]
        + datasets[i]["2ndFlrSF"]
    )
    datasets[i]["TotalBathrooms"] = (
        datasets[i]["BsmtFullBath"]
        + 0.5 * datasets[i]["BsmtHalfBath"]
        + datasets[i]["FullBath"]
        + 0.5 * datasets[i]["HalfBath"]
    )
    datasets[i]["TotalPorchSF"] = (
        datasets[i]["3SsnPorch"]
        + datasets[i]["EnclosedPorch"]
        + datasets[i]["OpenPorchSF"]
        + datasets[i]["ScreenPorch"]
    )
    datasets[i]["hasPool"] = datasets[i]["PoolArea"].apply(lambda x: 1 if x > 0 else 0)
    datasets[i]["has2ndfloor"] = datasets[i]["2ndFlrSF"].apply(lambda x: 1 if x > 0 else 0)
    datasets[i]["hasGarage"] = datasets[i]["GarageArea"].apply(lambda x: 1 if x > 0 else 0)
    datasets[i]["hasBsmt"] = datasets[i]["TotalBsmtSF"].apply(lambda x: 1 if x > 0 else 0)
    datasets[i]["hasFireplace"] = datasets[i]["Fireplaces"].apply(lambda x: 1 if x > 0 else 0)

# df_train[["TotalSF", "TotalFinSF", "TotalBathrooms", "TotalPorchSF"]].head(20)


# In[38]:


# カテゴリ変数のエンコーディング

# lightGBMに突っ込むためには数値型(またはbool型)である必要があるので、object型のデータをlabel encodingで処理する
# https://qiita.com/Hyperion13fleet/items/afa49a84bd5db65ffc31　こっちのほうが便利？

from sklearn.preprocessing import OrdinalEncoder
from sklearn.model_selection import train_test_split
from sklearn.model_selection import KFold
from lightgbm import LGBMRegressor, plot_tree
from sklearn.metrics import root_mean_squared_error as rmse
from sklearn.metrics import mean_absolute_percentage_error as mape

# object型のデータが入っている列を抽出
object_columns = df_train.select_dtypes(include="object").columns
df_train_pre_encoding = df_train.copy()
df_test_pre_encoding = df_test.copy()

# ラベルエンコーディング
oe = OrdinalEncoder()
df_train[object_columns] = oe.fit_transform(df_train[object_columns])
df_test[object_columns] = oe.fit_transform(df_test[object_columns])

print("df_train_pre_encoding")
display(df_train_pre_encoding.head(3))
print("df_train")
display(df_train.head(3))


# In[62]:


# # ラベルエンコーディング後に改めて相関係数行列を表示してみる
# corr_matrix = df_train.corr(numeric_only=True)

# plt.figure(figsize=(24, 20))
# sns.heatmap(abs(corr_matrix), annot=True, fmt=".1f", annot_kws={"fontsize": 6})

# カテゴリ変数を含めて相関をみたいのなら、カテゴリ変数の順位関係を考慮したラベル付けをしておかねばなるまい
# しかし現状はそうはなっていない…
# plt.suptitle("訓練データの相関係数(絶対値)行列_ラベルエンコーディング後")
# plt.show()


# In[67]:


X = df_train.drop(["SalePrice"], axis=1)
y = df_train["SalePrice"]

# クロスバリデーション
kf = KFold(n_splits=4, shuffle=True, random_state=42)

scores = []
params = {}
# params = {"max_depth": 19, "learning_rate": 0.1}
# パラメータチューニングにはoptunaというのを使うと良いらしい
# https://qiita.com/tetsuro731/items/a19a85fd296d4b87c367
# https://qiita.com/tetsuro731/items/76434194bab336a97172

for fold_idx, (tr_idx, va_idx) in enumerate(kf.split(X)):
    print(f"分割 {fold_idx + 1} / {kf.n_splits}")

    X_tr, X_va = X.iloc[tr_idx], X.iloc[va_idx]
    y_tr, y_va = y.iloc[tr_idx], y.iloc[va_idx]

    model = LGBMRegressor(**params)
    # GBDTのパラメータについて。https://knknkn.hatenablog.com/entry/2021/06/29/125226
    model.fit(X_tr, y_tr)
    y_pred = model.predict(X_va)

    score = rmse(np.log1p(y_pred), np.log1p(y_va))
    print(f"スコア(rmse(np.log1p(y_pred), np.log1p(y_va)): {score}")
    mape_ = mape(y_pred, y_va) * 100
    print(f"MAPE (平均絶対誤差率): {mape_:.2f}%")
    rmspe = np.sqrt(np.mean(np.square((y_va - y_pred) / y_va))) * 100
    print(f"RMSPE (平均平方二乗誤差率): {rmspe:.2f}%")
    print("\n")

    scores.append(score)

print(f"{fold_idx + 1}個のモデルのスコアの平均値: {np.mean(scores)}.")

# メモ：[LightGBM] [Warning] No further splits with positive gain, best gain: -infについて
# これは「決定木の作成中、これ以上分岐を作っても予測誤差が下がらなかったのでこれ以上分岐をさせなかった」ことを意味するらしい


# In[64]:


# 学習結果の図示(ここで表示しているのはクロスバリデーションの最後の分割時のモデルについて)
tree_idx = 0
print(f"{tree_idx + 1}番目の木の様子は以下の通り")


plot_tree(model, tree_index=tree_idx, figsize=(20, 10))

# 特徴量重要度
df_feature_importances = pd.DataFrame(
    {"feature_name": model.feature_name_, "importance": model.feature_importances_}
).sort_values("importance", ascending=False)

plt.figure(figsize=(16, 8))
sns.barplot(data=df_feature_importances, x="feature_name", y="importance")
plt.xticks(rotation=90)
plt.show()


# In[65]:


# 一度このまま提出用のデータを出力
model = LGBMRegressor(max_depth=-1)
model.fit(X, y)
sub_pred = model.predict(df_test)
submission = pd.DataFrame({"Id": df_test_Id, "SalePrice": sub_pred})
submission.to_csv(r"train_test_submission\submission.csv", index=False)

