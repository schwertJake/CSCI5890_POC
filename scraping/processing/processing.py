import json
import time
from nltk.stem import PorterStemmer
import nltk

class LyricAnalyst:

    def __init__(self):

        # Aggregator Values:
        self.perc_agreed_sum = 0.0
        self.unique_word_count_sum = 0
        self.total_word_count_sum = 0
        self.repetition_count_sum = 0.0
        self.records_processed = 0
        self.elapsed_time_sum = 0.0

        nltk.download('punkt')
        nltk.download('averaged_perceptron_tagger')
        self.ps = PorterStemmer()   # Word Stemmer
        self.union_dict = {}        # Dict for lyric BoW Unions

    def get_lyric_stats(self, lyrics_list: list) -> dict:
        """
        Top Level stat to get analysis of lyrics content

        :param lyrics_list: list of lyric dictionaries
        :return:
        """
        start = time.time()
        bow_list = []
        source_count = 0
        for lyrics in lyrics_list:
            for key, val in lyrics.items():
                if val == "":
                    continue
                else:
                    bow_list.append({key: self._bag_of_words_stemmed(val)})
                    source_count += 1
        if len(bow_list) == 0:
            return {}
        elif len(bow_list) == 1:
            stats = self._BoW_union_stats_single(bow_list[0], source_count)
        else:
            stats = self._BoW_union_stats_multiple(bow_list, source_count)
        self._increment_aggr_values(stats)

        self.elapsed_time_sum += (time.time() - start)
        return stats

    def get_usage_report(self):
        """
        Returns usage statistics of the processing module

        :return: dict of form {
            "Processing_Usage_Report": {
                "Total_Records_Processed": int,
                "Avg_Perc_Agreed": float,
                "Avg_Unique_Word_Count": float,
                "Avg_Total_Word_Count": float,
                "Avg_Repetitions_Count": float,
                "Avg_Analysis_Time_ms": float
            }
        }
        """
        count = self.records_processed
        if count == 0:
            return {}
        usage = {
            "Processing_Usage_Report": {
                "Total_Records_Processed": count,
                "Avg_Perc_Agreed": self.perc_agreed_sum / count,
                "Avg_Unique_Word_Count": self.unique_word_count_sum / count,
                "Avg_Total_Word_Count": self.total_word_count_sum / count,
                "Avg_Repetitions_Count": self.repetition_count_sum / count,
                "Avg_Analysis_Time_ms": self.elapsed_time_sum / count * 1000.0
            }
        }
        return usage

    def clear_usage_stats(self):
        self.perc_agreed_sum = 0.0
        self.unique_word_count_sum = 0
        self.total_word_count_sum = 0
        self.repetition_count_sum = 0.0
        self.records_processed = 0
        self.elapsed_time_sum = 0.0

    def _bag_of_words_stemmed(self, lyrics: str) -> dict:
        """
        Takes a string of words, stems each words
        and creates a word bag of the word count.

        :param lyrics: string of flattened lyrics
        :return: bag of words as dict
        """
        ret_dict = {}
        lyric_list = lyrics.split()
        for word in lyric_list:
            stemmed_word = self.ps.stem(word)
            if stemmed_word in ret_dict.keys():
                ret_dict[stemmed_word] += 1
            else:
                ret_dict[stemmed_word] = 1
        return ret_dict

    def _BoW_union_stats_multiple(self, list_of_bows: list,
                                  source_count: int) -> dict:
        """
        Takes a list of BoW dictionaries, wraps the functionality of
        self._BoW_union_raw and converts the output into usable statistic.
        Packs those statistics into a dictionary that it returns

        :param list_of_bows: list of BoW dicts
        :param source_count: number of lyric source (int)
        :return: dict of form {
            "Percent_Agreed": int,
            "Unique_Word_Count": int,
            "Total_Word_Count": int,
            "Repetition_Coeff": float,
            "Lyric_Sources": int,
            "BoW_Shared": dict of form {
                "word": count
            }
        }
        """
        raw_union = self._BoW_union_raw(list_of_bows)
        same_BoW = {}
        same_word_count = 0
        dif_word_count = 0

        for key, val in raw_union["Same"].items():
            same_BoW[key] = val["Count"]
            same_word_count += same_BoW[key]

        for key, val in raw_union["Different"].items():
            min_val = 10000
            for sources in val:
                count = sources["Count"]
                if count > min_val:
                    dif_word_count += (count - min_val)
                else:
                    min_val = count
            same_BoW[key] = min_val
            same_word_count += min_val

        for key, val in raw_union["Unique"].items():
            dif_word_count += raw_union["Unique"][key]["Count"]


        r = []
        for key, val in same_BoW.items():
            r.append({
                "Word": key,
                "Count": val,
                "POS_Type": nltk.pos_tag([key])[0][1]
            })

        perc_agreed = same_word_count / (same_word_count + dif_word_count)
        return {
            "Percent_Agreed": perc_agreed,
            "Unique_Word_Count": len(same_BoW.keys()),
            "Total_Word_Count": sum([val for val in same_BoW.values()]),
            "Repetition_Coeff":
                len(same_BoW.keys()) /
                sum([val for val in same_BoW.values()]),
            "Lyric_Sources": source_count,
            "BoW_Shared": r
        }

    def _BoW_union_stats_single(self, bow_raw: dict,
                                source_count: int) -> dict:
        """
        Provides statistics for a single Bag of Words

        :param bow_raw: raw BoW dictionary for single lyric source
        :param source_count: number of lyric source (int)
        :return: dict of form {
            "Percent_Agreed": int,
            "Unique_Word_Count": int,
            "Total_Word_Count": int,
            "Repetition_Coeff": float,
            "Lyric_Sources": int,
            "BoW_Shared": dict of form {
                "word": count
            }
        }
        """
        bow = bow_raw[list(bow_raw.keys())[0]]
        r = []
        for key,val in bow.items():
            r.append({
                "Word": key,
                "Count": val,
                "POS_Type": nltk.pos_tag([key])[0][1]
            })
        return {
            "Percent_Agreed": 1,
            "Unique_Word_Count": len(bow.keys()),
            "Total_Word_Count": sum([val for val in bow.values()]),
            "Repetition_Coeff": len(bow.keys()) /
                                sum([val for val in bow.values()]),
            "Lyric_Sources": source_count,
            "BoW_Shared": r
        }

    def _BoW_union_raw(self, bows_raw_list: list) -> dict:
        """
        Takes a list of BoWs, and unions the into a dict that looks like:
        {
            "Same": {
                "word": {
                    "Sources": [],
                    "Count": int
                },
            }
            "Different": {
                "word": [
                    {
                        "Sources": [],
                        "Count": int
                    },
                    {
                        "Sources": [],
                        "Count": int
                    },
                ]
            }
            "Unique": {
                "word": {
                    "Sources": [],
                    "Count": int
                }
            }
        }
        :param bows_raw_list: list of BoW Dictionaries
        :return: dict of form above
        """
        self.union_dict = {"Same": {},
                           "Different": {},
                           "Unique": {}}
        bow_names = []
        bows_list = []
        for bow in bows_raw_list:
            for key, val in bow.items():
                bow_names.append(key)
                bows_list.append(val)

        for i in range(len(bows_list)):

            for key, val in bows_list[i].items():

                if key in self.union_dict["Unique"]:
                    self._handle_BoW_union_key_in_unique(key=key, val=val, i=i,
                                                         bow_names=bow_names)

                elif key in self.union_dict["Same"]:
                    self._handle_BoW_union_key_in_same(key=key, val=val, i=i,
                                                       bow_names=bow_names)

                elif key in self.union_dict["Different"]:
                    self._handle_BoW_union_key_in_Dif(key=key, val=val, i=i,
                                                      bow_names=bow_names)

                else:
                    self.union_dict["Unique"][key] = {
                        "Sources": [bow_names[i]],
                        "Count": val
                    }

        return self.union_dict

    def _handle_BoW_union_key_in_unique(self, key: str, val: int,
                                        i: int, bow_names: list):
        """
        If the word is already in unique, that means we need to check
        if new count is the same. If it is, move it to "Same" subdict,
        otherwise move it to "Different" subdict

        :param key: word (str)
        :param val: count of word (int)
        :param i: loop control variable (num of lyric sources)
        :param bow_names: name of BoW sources
        :return: None
        """
        # Store the values that already exist and
        # Get rid of the entry
        compare_val = self.union_dict["Unique"][key]["Count"]
        init_source = self.union_dict["Unique"][key]["Sources"]
        del self.union_dict["Unique"][key]

        # If the word counts match, move word to "Same" sub dict
        if val == compare_val:
            self.union_dict["Same"][key] = {
                "Sources": init_source,
                "Count": val
            }
            self.union_dict["Same"][key]["Sources"].append(bow_names[i])

        # If they don't, move them to "Different" sub dict
        else:
            self.union_dict["Different"][key] = [{
                "Sources": init_source,
                "Count": compare_val
            }, {
                "Sources": [bow_names[i]],
                "Count": val
            }
            ]

    def _handle_BoW_union_key_in_same(self, key: str, val: int,
                                      i: int, bow_names: list):
        """
        If the key is already in the "Same" subdict, we need to check if
        the new value continues to be the same, or if it is different and needs
        to be moved to the "Different" subdict

        :param key: word (str)
        :param val: count of word (int)
        :param i: loop control variable (num of lyric sources)
        :param bow_names: name of BoW sources
        :return: None
        """
        # Store the values that already exist
        compare_val = self.union_dict["Same"][key]["Count"]
        init_sources = self.union_dict["Same"][key]["Sources"]

        # If all counts are still agreed upon, add source name to list
        if val == compare_val:
            self.union_dict["Same"][key]["Sources"].append(bow_names[i])

        # If they aren't agreed upon, word gets moved to "Different"
        else:
            del self.union_dict["Same"][key]
            self.union_dict["Different"][key] = [
                {
                    "Sources": init_sources,
                    "Count": compare_val
                },
                {
                    "Sources": [bow_names[i]],
                    "Count": val
                }
            ]

    def _handle_BoW_union_key_in_Dif(self, key: str, val: int,
                                     i: int, bow_names: list):
        """
        If the key is in the "Different" subdict, we need to check if
        the new value matches any of the existing values, if not if gains
        its own entry in the word's source list

        :param key: word (str)
        :param val: count of word (int)
        :param i: loop control variable (num of lyric sources)
        :param bow_names: name of BoW sources
        :return: None
        """
        # Add new source name to list
        changed = False
        for counts in self.union_dict["Different"][key]:
            if counts["Count"] == val:
                counts["Sources"].append(bow_names[i])
                changed = True
        if not changed:
            self.union_dict["Different"][key].append({
                "Sources": [bow_names[i]],
                "Count": val
            })

    def _increment_aggr_values(self, stats: dict):
        """
        Increments aggregator values to gain insight into stats
        of total dataset

        :param stats: dict of stats from _BoW_union_stats
        :return: None
        """
        self.perc_agreed_sum += stats["Percent_Agreed"]
        self.unique_word_count_sum += stats["Unique_Word_Count"]
        self.total_word_count_sum += stats["Total_Word_Count"]
        self.repetition_count_sum += stats["Repetition_Coeff"]
        self.records_processed += 1


if __name__ == "__main__":

    LA = LyricAnalyst()

    s1 = "worda wordb wordc wordd worda wordb wordc wordd worda wordb wordc wordd"
    s2 = "worda wordb wordc wordd worda wordb wordc wordd worda wordb wordc wordd"
    s3 = "worda wordb wordc wordd worda wordb wordc wordd worda wordb wordf wordg"

    results = LA.get_lyric_stats([{"s1": s1}, {"s2": s2}, {"s3": s3}])

    json_dump = json.dumps(results, indent=4)
    print(json_dump)

    usage = LA.get_usage_report()
    json_dump = json.dumps(usage, indent=4)
    print(json_dump)
