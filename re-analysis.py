#!/usr/bin/env python
# coding: utf-8

# # 1. EDA

# In[50]:


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


# In[51]:


print("-" * 10, "df_train.columns", "-" * 10)
print(df_train.columns)


# In[52]:


print("-" * 10, 'df_train["SalePrice"].describe()', "-" * 10)
print(df_train["SalePrice"].describe())

# SalePriceの分布
sns.histplot(df_train["SalePrice"], kde=True)
plt.suptitle("目的変数SalePriceの分布")
plt.show()


# In[53]:


corr_matrix = df_train.corr(numeric_only=True)
"""
    訓練データdf_trainの相関係数行列
    corr_matrix = df_train.corr(numeric_only=True)
"""

plt.figure(figsize=(12, 10))
sns.heatmap(abs(corr_matrix), annot=True, fmt=".1f", annot_kws={"fontsize": 6})

plt.suptitle("訓練データの相関係数(絶対値)行列_カテゴリ変数を除く")
plt.show()


# In[54]:


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

# In[55]:


# 外れ値処理(訓練データ)
# 外れ値のインデックス番号は、plotlyで描いたグラフから得た
df_train_befdrop = df_train
df_train = df_train.drop(df_train.index[[523, 1298]])

fig = px.scatter(
    df_train, x="GrLivArea", y="SalePrice",
    opacity=0.3,
    hover_data=[df_train.index]
)

fig.update_layout(
    title_text="SalePrice vs GrLivArea. 外れ値処理後",
    showlegend=False,
    height=500,
    width=600
)

# グラフの表示
fig.show()


# In[56]:


# 欠損値処理(訓練データ、テストデータ)
df_all_data = pd.concat([df_train, df_test])

df_missing_values_count = df_all_data.isna().sum()
df_missing_values_table = pd.DataFrame(
    {
        "Missing_count": df_missing_values_count,
        "Percent (%)": round(df_missing_values_count / len(df_all_data) * 100, 2)
    }
).sort_values("Missing_count", ascending=False)

# chatGPTに作ってもらった各特徴量の説明をまとめたcsvを読み込み、欠損値に関する表と結合
df_data_description = pd.read_csv("data_description/data_descripsion_simple_jp.csv", index_col=0)
df_missing_value_description = pd.concat([df_missing_values_table, df_data_description], axis=1)

# csvに出力。これとydata_profilingのレポートを眺めながら各欠損値をどう処理するか考える。
if not os.path.exists("missing_value"):
    os.makedirs("missing_value")
df_missing_value_description.to_csv(
    "missing_value/missing_value_processing.csv", encoding="utf-8_sig"
)

display(df_missing_value_description.head(15))


# In[57]:


# LotFrontageの欠損割合が多いが、何で補完するかが難しい。どれかのカテゴリ変数に対する傾向がないか調べてみる

# object型のデータが入っている列を抽出
object_columns = df_all_data.select_dtypes(include="object").columns

# プロットのサイズを指定
num_cols = len(object_columns)
rows = num_cols // 6 + 1  # 行数
cols = 6  # 列数

# サブプロットの作成
fig = sp.make_subplots(
    rows=rows, 
    cols=cols, 
    subplot_titles=[f"{col} vs LotFrontage" for col in object_columns],
    )

# object_columnsにある特徴量ごとに箱ひげ図を描く
for i, col in enumerate(object_columns):
    row = i // cols + 1
    col_num = i % cols + 1
    box = px.box(df_all_data, x=col, y="LotFrontage")
    for trace in box.data:
        fig.add_trace(trace, row=row, col=col_num)
    fig.update_annotations()

# グラフのタイトルを設定
fig.update_layout(
    title_text=f"各カテゴリ変数に対するLotFrontageの箱ひげ図",
    showlegend=False,
    height=400 * rows,
    width=1600,
)

# グラフの表示
fig.show()


# In[58]:


# x="Neighborhood", y="LotFrontage"が傾向を捉えていそう。詳しく確認する

fig = px.box(df_all_data, x="Neighborhood", y="LotFrontage")

fig.update_layout(
    # title_text=" ",
    showlegend=False,
    height=500,
    width=1000
)

# グラフの表示
fig.show()


# In[59]:


# 各地域"Neighborhood"の"LotFrontage"の中央値で欠損値を補完する

df_medLot_groupby_Neighborhood = df_all_data.groupby(by="Neighborhood")["LotFrontage"].agg("median")

def fillnaLot(row):
    """
    ある1つの住宅データについて、"LotFrontage"列の値が欠損している場合はそのデータの地域（"Neighborhood"）の"LotFrontage"の中央値を返す。
    欠損していない場合、元の値をそのまま返す。

    Args:
        row (pd.Series): "LotFrontage"列の欠損値処理をしたいデータ

    Return
    -------
        "LotFrontage"列が…
            欠損の場合: df_group_LotFrontage[row["Neighborhood"]]
            欠損でない場合: row["LotFrontage"]
    """
    if pd.isna(row["LotFrontage"]):
        return df_medLot_groupby_Neighborhood[row["Neighborhood"]]
    else:
        return row["LotFrontage"]


# In[60]:


# LotFrontageの補完
df_all_data["LotFrontage"] = df_all_data.apply(fillnaLot, axis=1)

# "None"で補完
cols_fillNone = [
    "MiscFeature",
    "Alley",
    "Fence",
    "MasVnrType",
    "FireplaceQu",
    "GarageFinish",
    "GarageQual",
    "GarageCond",
    "GarageType",
    "BsmtCond",
    "BsmtExposure",
    "BsmtQual",
    "BsmtFinType2",
    "BsmtFinType1"    
]
# 0で補完
cols_fill0 = [
    "GarageYrBlt",
    "MasVnrArea",
    "BsmtHalfBath",
    "BsmtFullBath",
    "GarageArea",
    "GarageCars",
    "BsmtFinSF1",
    "BsmtFinSF2",
    "BsmtUnfSF",
    "TotalBsmtSF"
]
# 最頻値で補完
cols_fillmode = [
    "MSZoning",
    "Functional",
    "Exterior2nd",
    "Exterior1st",
    "SaleType",
    "KitchenQual",
    "Electrical"
]
# 列削除：PoolQC(99.7%が欠損)、Utilities(99.6%が"allpub")、PoolArea(99.6%が0)
cols_drop = [
    "PoolQC",
    "Utilities",
    "PoolArea"
]

for col in cols_fillNone:
    df_all_data[col] = df_all_data[col].fillna("None")
for col in cols_fill0:
    df_all_data[col] = df_all_data[col].fillna(0)
for col in cols_fillmode:
    df_all_data[col] = df_all_data[col].fillna(df_all_data[col].mode()[0])
df_all_data = df_all_data.drop(columns=cols_drop)


# In[61]:


# 特徴量エンジニアリング(訓練データ、テストデータ)
# 新しい特徴量の作成
# 'YrBltAndRemod': 'YearBuilt' + 'YearRemodAdd'

df_all_data["TotalSF"] = (
    df_all_data["TotalBsmtSF"]
    + df_all_data["1stFlrSF"] 
    + df_all_data["2ndFlrSF"]
)
df_all_data["TotalFinSF"] = (
    df_all_data["BsmtFinSF1"]
    + df_all_data["BsmtFinSF2"]
    + df_all_data["1stFlrSF"]
    + df_all_data["2ndFlrSF"]
)
df_all_data["TotalBathrooms"] = (
    df_all_data["BsmtFullBath"]
    + 0.5 * df_all_data["BsmtHalfBath"]
    + df_all_data["FullBath"]
    + 0.5 * df_all_data["HalfBath"]
)
df_all_data["TotalPorchSF"] = (
    df_all_data["3SsnPorch"]
    + df_all_data["EnclosedPorch"]
    + df_all_data["OpenPorchSF"]
    + df_all_data["ScreenPorch"]
)

df_all_data["has2ndfloor"] = df_all_data["2ndFlrSF"].apply(lambda x: 1 if x > 0 else 0)
df_all_data["hasGarage"] = df_all_data["GarageArea"].apply(lambda x: 1 if x > 0 else 0)
df_all_data["hasBsmt"] = df_all_data["TotalBsmtSF"].apply(lambda x: 1 if x > 0 else 0)
df_all_data["hasFireplace"] = df_all_data["Fireplaces"].apply(lambda x: 1 if x > 0 else 0)

df_all_data[[
    "TotalSF",
    "TotalFinSF",
    "TotalBathrooms",
    "TotalPorchSF",
    "has2ndfloor",
    "hasGarage",
    "hasBsmt",
    "hasFireplace"    
]].head(5)


# In[62]:


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
object_columns = df_all_data.select_dtypes(include="object").columns
# エンコード前に退避
df_all_data_pre_encoding = df_all_data.copy()

# one-hot encoding
df_all_data = pd.get_dummies(df_all_data).reset_index(drop=True)

print(f"df_all_data_pre_encoding.shape: {df_all_data_pre_encoding.shape}")
display(df_all_data_pre_encoding.head(3))
print(f"df_all_data.shape: {df_all_data.shape}")
display(df_all_data.head(3))


# In[63]:


# モデル構築

# まず、df_all_dataをdf_trainとdf_testに分割し直す
ntrain = len(df_train)

df_train = df_all_data[:ntrain]
df_test = df_all_data[ntrain:].drop(["SalePrice"], axis=1)


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

# 重要度が一定以上のものだけ抽出
threshold = 5.0
df_feature_importances_filterd = df_feature_importances[df_feature_importances["importance"] >= threshold]

plt.figure(figsize=(16, 8))
sns.barplot(data=df_feature_importances_filterd, x="feature_name", y="importance")
plt.suptitle(f"特徴量重要度(≧{threshold}のものを抽出)")
plt.xticks(rotation=90)
plt.show()


# In[65]:


# 一度このまま提出用のデータを出力
model = LGBMRegressor(max_depth=-1)
model.fit(X, y)
sub_pred = model.predict(df_test)
submission = pd.DataFrame({"Id": df_test_Id, "SalePrice": sub_pred})
submission.to_csv("train_test_submission/submission.csv", index=False)

