#coding:utf-8
import struct
from binascii import *
import argparse
import sys
import time
class  IllegalException(Exception):
	def __init__(self,msg):
		Exception.__init__(self,msg)
class Read_fat16(object):
	def __init__(self):
		self.bdr_length = 512
		self.f = open('fs.bin','rb+')
		self.str = ''
		self.curr_needed = 1	
		self.bpb_list = []
		self.DirectoryName = {}
		self.start_cluster = 0
		self.directory_start_cluster = None			#如果command命令带有指定目录，则该值就不会为None
	def read_bpb(self):								#内共享BPB列表
		self.f.seek(11,0)
		bpb_string = self.f.read(25)
		info = struct.unpack('=HBHBHHBHHHII',bpb_string)
		BytesPerSector = info[0]
		SectorsPerClusters = info[1]
		#print SectorsPerClusters
		ReservedSectors = info[2]
		NumberOfCopiesOfFats = info[3]
		MaxRootDirEntries = info[4]
		NumberOfSectors = info[5]
		enum_MediaDescription = info[6]
		SectorsPerFat = info[7]
		SectorsPerTrack = info[8]
		NumHeadsPerCylinder = info[9]
		NumHiddenSectors = info[10]
		NumSectorInPartition = info[11]
		bpb_list = [BytesPerSector,					#每个扇区的字符数量
				SectorsPerClusters,				#每簇所占用的扇区数，则每簇占用的字节数为 list[0]*list[1]
				ReservedSectors,
				NumberOfCopiesOfFats,
				MaxRootDirEntries,
				NumberOfSectors,				#扇区数
				enum_MediaDescription,
				SectorsPerFat,					#每个fat表的扇区数量
				SectorsPerTrack,
				NumHeadsPerCylinder,
				NumHiddenSectors,
				NumSectorInPartition]
		self.bpb_list = bpb_list	
	def read_fat(self):							#scan fat表，将第一个空簇append进列表中，以备后续使用
		curr_not_used = []
		bpb_list = self.bpb_list
		fat_length = bpb_list[0] * bpb_list[7]	#512*40 = 20480th 这里和表格的簇是对应的
		fat_table = self.f.read(fat_length)		#读第一个fat表
		for i in range(0,fat_length,2):
			if hex(struct.unpack('=H',fat_table[i:i+2])[0]) == '0x0':
				curr_not_used.append(i)
				if len(curr_not_used) >= self.curr_needed:
					break
		start_cluster = curr_not_used[0]/2 
		self.f.seek(512+curr_not_used[0])			#这里我假定文件的大小固定小于一个簇的，逻辑可再完善
		self.f.write(struct.pack('=H',0xFFFF))
		print 'start cluster is',start_cluster
		self.start_cluster = start_cluster

	def read_fdt(self,filename):					
		content = self.fdt_content(filename)
		fdt_not_used = []
		if self.directory_start_cluster is not None:			#当存在指定目录写操作时，
			bpb_list = self.bpb_list
			fat_length = bpb_list[0] * bpb_list[7]  
			index = self.bdr_length + 2 * fat_length
			start_cluster = self.start_cluster            		#起始簇还是从fat表中去读
			print 'the sub dir file start cluster is',start_cluster
			sub_dir_content,sub_dir_data_offset = self.read_data(self.directory_start_cluster,filename)		#这里是子目录在父目录的data区该写入的fdt以及偏移
			#print b2a_hex(sub_dir_content[:50])
			for i in range(0,32*512,32):
				if b2a_hex(struct.unpack('=8s3sBHHHHHHHHL',sub_dir_content[i:i+32])[0])[0:8] == '00000000':
					fdt_not_used.append(i)
					break
			#print 'sub dir fdt not used offset is',fdt_not_used[0]
			#fdt_index = index + fdt_not_used[0]/32 * 32
			print 'sub dir fdt not used is',fdt_not_used[0]
			fdt_index = sub_dir_data_offset + fdt_not_used[0]/32*32							#这里的偏移是父目录data的偏移加上i的偏移
			#print 'director fdt offset is:',hex(fdt_index)
			self.f.seek(fdt_index)
			fdt_content = struct.pack('=8s3sBHHHHHHHHI',content[0],content[1],content[2],content[3],content[4], \
				content[5],content[6],content[7],content[8],content[9],start_cluster,150)
			self.f.write(fdt_content)														#写完fdt接着写data

			ReservedSectors = bpb_list[2]
			NumberOfCopiesOfFats = bpb_list[3]
			SectorsPerFat = bpb_list[7]
			BytesPerSector = bpb_list[0]
			SectorsPerClusters = bpb_list[1]
			data_offset = ((start_cluster-2)*SectorsPerClusters + ReservedSectors + 32 + NumberOfCopiesOfFats*SectorsPerFat)*512
			print 'data offset is:',hex(data_offset)
			self.f.seek(data_offset)
			sub_dir_file_content = struct.pack('150s','W'*150)
			self.f.write(sub_dir_file_content)
			print 'data has setted'

		else:
			start_cluster = self.start_cluster
			bpb_list = self.bpb_list
			fat_length = bpb_list[0] * bpb_list[7]  
			index = self.bdr_length + 2 * fat_length
			#print 'fdt offset is:',index
			self.f.seek(index)
			fdt_table = self.f.read(32*512)    #固定写死
			for i in range(0,32*512,32):
				if b2a_hex(struct.unpack('=8s3sBHHHHHHHHL',fdt_table[i:i+32])[0])[0:8] == '00000000':
					fdt_not_used.append(i)
					break
			fdt_index = index + fdt_not_used[0]/32 * 32
			print 'fdt offset is:',hex(fdt_index)
			self.f.seek(fdt_index)
			fdt_content = struct.pack('=8s3sBHHHHHHHHI',content[0],content[1],content[2],content[3],content[4], \
				content[5],content[6],content[7],content[8],content[9],start_cluster,150)
			self.f.write(fdt_content)
			self.read_data(self.start_cluster,filename)

	def read_data(self,D_start_cluster,filename):		
		bpb_list = self.bpb_list
		start_cluster = D_start_cluster
		print start_cluster
		ReservedSectors = bpb_list[2]
		NumberOfCopiesOfFats = bpb_list[3]
		SectorsPerFat = bpb_list[7]
		BytesPerSector = bpb_list[0]
		SectorsPerClusters = bpb_list[1]
		data_offset = ((start_cluster-2)*SectorsPerClusters + ReservedSectors + 32 + NumberOfCopiesOfFats*SectorsPerFat)*512
		print 'data offset is:',hex(data_offset)
		self.f.seek(data_offset)
		#content = struct.pack('150s','X'*150)
		#self.f.write(content)
		#print 'data has setted'
		if self.directory_start_cluster is not None:
			sub_dir_content = self.f.read(2048)
			return sub_dir_content,data_offset
		else:
			content = struct.pack('150s','M'*150)
			self.f.write(content)
			print 'data has setted'
			
	def fdt_content(self,filename):
		name,extension = filename.split('.')
		create_time = time.time()
		local = time.localtime(create_time)
		year = local.tm_year - 1980
		month = local.tm_mon
		day = local.tm_mday
		date = (year << 9) | (month << 5) | (day & 0x1f)
		attribute = 0x20
		reserved = 0x18
		createtime = 0x0
		createdate = date
		accessdate = date
		highcluster = 0x0
		updatetime = 0x0
		updatedate = date
		return [name,extension,attribute,reserved,createtime,createdate,accessdate,highcluster,updatetime,updatedate]

	def find_directory(self,filename,path):							#找fat文件所有的目录，其原理在于找其属性为10（目录）
		bpb_list = self.bpb_list
		fat_length = bpb_list[0] * bpb_list[7]  
		index = self.bdr_length + 2 * fat_length
		self.f.seek(index)
		fdt_table = self.f.read(32*512)
		for i in range(0,32*512,32):
			if b2a_hex(fdt_table[i+11]) == '0F':					#这里长文件名不能够太大
				i += 32												#长文件名+=32 直接到short部分
				if b2a_hex(fdt_table[i+11]) == '10':
					DirecName = fdt_table[i:i+8].strip()	
					self.DirectoryName[DirecName] = struct.unpack('=H',fdt_table[i+26:i+28])[0]
				else:
					raise IllegalException('Long fileName error,cause i can\'t convert it right' )
			elif b2a_hex(fdt_table[i+11]) == '10':
				DirecName = fdt_table[i:i+8].strip()	
				self.DirectoryName[DirecName] = struct.unpack('=H',fdt_table[i+26:i+28])[0]
		print 'directory list is:',self.DirectoryName
		if path is not None:
			if path in self.DirectoryName.keys():
				self.directory_start_cluster = self.DirectoryName[path]
				print '{} path start cluster is {}'.format(path,self.DirectoryName[path])			
			else:
				raise IllegalException('{} is not found! please check again'.format(path))

if __name__=='__main__':
	parser = argparse.ArgumentParser(description="unit selector",add_help=False)
	parser.add_argument("--command",action="store",dest='command',required='True')
	args = parser.parse_args()
	command = args.command			#touch /boot/hua.txt
	if 'touch' in command and command.count('/') == 2:
		_,path,filename = command.split('/')
	elif 'touch' in command and command.count('/') == 0:
		path = None
		_,filename = command.split(' ')
	else:
		raise IllegalException('command must start with touch,cause i only support create file and dir-deepth must equals 2')
	
	myjob = Read_fat16()
	myjob.read_bpb()
	myjob.find_directory(filename,path)
	myjob.read_fat()
	myjob.read_fdt(filename)
