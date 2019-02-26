class UserBasedCF:
    def __init__(self, df_ratings, df_movies):
        self.df_ratings = df_ratings
        self.df_movies = df_movies
    
    def get_list_movie(self, uid, df=None):
        
        if not df:
            df = self.df_ratings
            
        cur_df = df[df["userId"] == uid]
        movies = list(cur_df["movieId"])[0]
        rating = list(cur_df["rating"])[0]
        return movies, rating


    def get_same_movies(self, movies1, movies2):
        movies1 = set(movies1)
        result = []
        for x in movies2:
            if x in movies1:
                result.append(x)
        return result


    def build_dict_rating(self, movies, ratings):
        result = dict()
        for i, val in enumerate(movies):
            result[val] = ratings[i]
        return result


    def calc_mean_rating(self, ratings):
        return sum(ratings) / len(ratings)


    def calc_std(self, ratings, mean_rating):
        if len(ratings) < 1:
            return 1

        if len(ratings) < 2:
            return ratings[0] - mean_rating

        return (sum((r - mean_rating)**2 for r in ratings) / (len(ratings) - 1))**0.5


    def calc_z_score(self, rating, mean_rating, std_rating):
        return (rating - mean_rating) / std_rating


    def calc_similarity(self, 
                        u_uid, 
                        df=None, 
                        use_discount_sim=False, 
                        discount_sim_threshold=5
                       ):
        if not df:
            df = self.df_ratings
        
        u_movies, u_ratings = self.get_list_movie(u_uid)
        u_rating_dict = self.build_dict_rating(u_movies, u_ratings)
        u_mean_rating = self.calc_mean_rating(u_ratings)

        for row in df.iterrows():
            if row[1]["userId"] != u_uid:
                v_uid = row[1]["userId"]
                v_movies, v_ratings = self.get_list_movie(v_uid)
                v_rating_dict = self.build_dict_rating(v_movies, v_ratings)
                v_mean_rating = self.calc_mean_rating(v_ratings)

                same_movies = self.get_same_movies(u_movies, v_movies)

                if len(same_movies) <= 0:
                    continue

                up_value = 0
                for m in same_movies:
                    up_value += (u_rating_dict[m] - u_mean_rating) * (v_rating_dict[m] - v_mean_rating)

                down_value1 = 0
                for m in same_movies:
                    down_value1 += (u_rating_dict[m] - u_mean_rating)**2
                down_value1 = down_value1**0.5

                down_value2 = 0
                for m in same_movies:
                    down_value2 += (v_rating_dict[m] - v_mean_rating)**2
                down_value2 = down_value2**0.5

                if down_value1 * down_value2 == 0:
                    continue

                similarity_value = up_value / (down_value1 * down_value2)

                if use_discount_sim:
                    similarity_value *= min(len(same_movies), discount_sim_threshold) / discount_sim_threshold

                yield similarity_value, len(same_movies), row[1]


    def suggest_new_movie(self, 
                          u_uid, 
                          df=None, 
                          top_k=50, 
                          use_discount_sim=False, 
                          discount_sim_threshold=5,
                          use_z_score=False
                         ):
        
        if not df:
            df = self.df_ratings
        
        similarities = list(x for x in self.calc_similarity(u_uid, use_discount_sim, discount_sim_threshold) if x[0] > 0)
        similarities = sorted(similarities, key=lambda x:x[0], reverse=True)

        u_movies, u_ratings = self.get_list_movie(u_uid)
        u_rating_dict = self.build_dict_rating(u_movies, u_ratings)
        u_mean_rating = self.calc_mean_rating(u_ratings)
        u_std = self.calc_std(u_ratings, u_mean_rating)

        all_movies = dict()
        for val in similarities[0:top_k]:
            for x in val[2]["movieId"]:
                all_movies[x] = 0

        for movie in all_movies.keys():
            have_rated = [x for x in similarities[0:top_k] if movie in x[2]["movieId"]]

            top_value = 0
            down_value = 0

            if not use_z_score:
                for v_user in have_rated:
                    v_movies, v_ratings = self.get_list_movie(v_user[2]["userId"])
                    v_rating_dict = self.build_dict_rating(v_movies, v_ratings)
                    v_mean_rating = self.calc_mean_rating(v_ratings)

                    sim_u_v = v_user[0]
                    top_value += sim_u_v * (v_rating_dict[movie] - v_mean_rating)
                    down_value += sim_u_v

                if down_value > 0:
                    all_movies[movie] = u_mean_rating + top_value / down_value
            else:
                for v_user in have_rated:
                    v_movies, v_ratings = self.get_list_movie(v_user[2]["userId"])
                    v_rating_dict = self.build_dict_rating(v_movies, v_ratings)
                    v_mean_rating = self.calc_mean_rating(v_ratings)
                    v_std = self.calc_std(v_ratings, v_mean_rating)

                    sim_u_v = v_user[0]
                    top_value += sim_u_v * self.calc_z_score(v_rating_dict[movie], v_mean_rating, v_std)
                    down_value += sim_u_v

                if down_value > 0:
                    all_movies[movie] = u_mean_rating + u_std * top_value / down_value

        all_movies = [(movie, all_movies[movie]) for movie in sorted(all_movies, key=all_movies.get, reverse=True)]
        return all_movies
    
    
    def show_result(self, 
                    uid, 
                    suggest_movies, 
                    top_k = 10, 
                    df_ratings=None, 
                    df_movies=None,
                    file_path="../data/show_result.csv"
                   ):
        
        if not df_ratings:
            df_ratings = self.df_ratings
            
        if not df_movies:
            df_movies = self.df_movies
        
        f = open(file_path, "w")

        movies, ratings = self.get_list_movie(uid)
        print("Watched movies: ")
        for m, r in zip(movies, ratings):
            print(movies_info[m], "rate: ", r)
            f.write(str(m) + "," + movies_info[m] + "," + str(r) + "\n")

        print("Suggest movies: ")
        for m, s in suggest_movies[:top_k]:
            print(movies_info[m], "scores: ", s)
            f.write(str(m) + "," + movies_info[m] + "," + str(s) + "\n")