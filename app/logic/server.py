from app.logic.terminal import Terminal
from app.database_connection.local_database import LocalDatabase
from app.logic.worker import Worker
from app.logic.registry_log import RegistryLog
from datetime import datetime

terminal_json = "../data/terminals.json"
workers_json = "../data/workers.json"
logs_json = "../data/registrations.json"


class DataInputError(BaseException):
    def __init__(self, message):
        self.message = message


class Server:
    def __init__(self):
        self.__database = LocalDatabase(terminal_json, workers_json, logs_json)
        self.__terminals_dict = self.__database.read_terminals()
        self.__workers_dict = self.__database.read_workers()
        self.__logs_dict = self.__database.read_logs()

    def add_terminal(self, term_id, term_name):
        if term_id not in self.__terminals_dict:
            new_term = Terminal(term_id, term_name)
            self.__terminals_dict[term_id] = new_term
            self.__database.write_terminals(self.__terminals_dict.values())
        else:
            raise DataInputError("Terminal with id: " + term_id + " already exist")

    def remove_terminal(self, term_id):
        if term_id in self.__terminals_dict:
            del self.__terminals_dict[term_id]
            self.__database.write_terminals(self.__terminals_dict.values())
        else:
            raise DataInputError("Terminal with id: " + term_id + " not exist")

    def add_worker(self, name, surname, worker_id):
        new_worker = Worker(name, surname, worker_id)
        if worker_id not in self.__workers_dict:
            self.__workers_dict[worker_id] = new_worker
            self.__database.write_workers(self.__workers_dict.values())
        else:
            raise DataInputError("Worker with id: " + worker_id + " already exist in database")

    def remove_worker(self, worker_id):
        if worker_id in self.__workers_dict:
            del self.__workers_dict[worker_id]
            self.__database.write_workers(self.__workers_dict.values())
        else:
            raise DataInputError("Worker with id: " + worker_id + " not exist")

    def add_card_to_worker(self, card_id, worker_id):
        if worker_id in self.__workers_dict:
            card_owner = self.get_card_owner(card_id)
            if card_owner is not None:
                raise DataInputError(
                    "Card with id: " + card_id + " already assigned to worker with id: " + card_owner.worker_id)
            self.__workers_dict[worker_id].cards.append(card_id)
            self.__database.write_workers(self.__workers_dict.values())
        else:
            raise DataInputError("Worker with id: " + worker_id + " not exist")

    def get_card_owner(self, card_id):
        for w in self.__workers_dict.values():
            if card_id in w.cards:
                return w
        return None

    def remove_card_from_worker(self, card_id):
        for w in self.__workers_dict.values():
            if card_id in w.cards:
                w.cards.remove(card_id)
                self.__database.write_workers(self.__workers_dict.values())
                return w.worker_id
        raise DataInputError("Card with id: " + card_id + " hasn't been signed to any worker")

    def register_card_in_system(self, card_id, term_id):
        """
        :return: card owner id or none if card without owner
        """
        card_owner = self.get_card_owner(card_id)
        if not self.terminal_in_database(term_id):
            raise DataInputError("Terminal with id: " + term_id + " not assigned in database")
        if card_owner is None:
            owner_id = None
        else:
            owner_id = card_owner.worker_id
        self.add_log(card_id, term_id, owner_id)
        return card_owner

    def terminal_in_database(self, term_id):
        return term_id in self.__terminals_dict

    def add_log(self, card_id, term_id, worker_id):
        time = datetime.now()
        self.__logs_dict[time] = RegistryLog(time, term_id, card_id, worker_id)
        self.__database.write_logs(self.__logs_dict.values())

    def is_any_terminal_registered(self):
        return bool(self.__terminals_dict)

    def get_workers(self):
        return self.__workers_dict

    def get_registered_logs(self):
        return self.__logs_dict

    def get_terminals(self):
        return self.__terminals_dict

    def report_log_from_day(self, date=datetime.now().date()):
        predicate = lambda k: datetime.strptime(k, "%Y-%m-%d %H:%M:%S.%f").date() == date
        filtered_keys = list(filter(predicate, self.__logs_dict.keys()))
        filtered_logs = list(map(lambda k: self.__logs_dict[k], filtered_keys))
        return filtered_logs

    def report_log_from_day_worker(self, worker_id, date=datetime.now().date()):
        logs_from_day = self.report_log_from_day(date)
        result_arr = []
        for log in logs_from_day:
            if log.worker_id == worker_id:
                result_arr.append(log)
        return result_arr

    def report_work_time_from_day_worker(self, worker_id, date=datetime.now().date()):
        worker_log_for_day = self.report_log_from_day_worker(worker_id, date)
        work_cycles = []
        for i in range(0, len(worker_log_for_day) - 1, 2):
            exit_date_str = worker_log_for_day[i + 1].time
            exit_date = datetime.strptime(exit_date_str, "%Y-%m-%d %H:%M:%S.%f")
            enter_date_str = worker_log_for_day[i].time
            enter_date = datetime.strptime(enter_date_str, "%Y-%m-%d %H:%M:%S.%f")
            result = exit_date - enter_date
            work_cycles.append(result)
        work_time = work_cycles[0]
        for i in range(1, len(work_cycles)):
            work_time += work_cycles[i]
        return work_time

    def report_work_time_from_day(self, date=datetime.now().date()):
        workers_time_list = []
        for worker_id in self.__workers_dict.keys():
            work_time = self.report_work_time_from_day_worker(worker_id, date)
            if work_time > work_time.min:
                workers_time_list.append({worker_id: work_time})
        return workers_time_list
